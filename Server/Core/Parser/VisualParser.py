"""
Pipeline to go from PDF → structured chunks via **layout-aware** extraction.

Unlike the text-only parser in ``Core.Embedder.parser``, this module preserves
the 2-D spatial layout of every page so that images can be paired with their
surrounding text (captions, explanations, questions) using bbox proximity.

Schema alignment (schema.sql)
-----------------------------
- ``core.chunks``  → text blocks with ``position_index`` & ``section_title``
- ``core.images``  → images with ``image_path``, ``caption``, ``position_index``
- ``core.chunk_image_links`` → spatial links between chunks ↔ images

Steps
-----
1. Parse PDF layout with PyMuPDF (``fitz``)
2. Extract images with bounding boxes
3. Extract text blocks with bounding boxes
4. Spatial association — link images to captions / context / questions
5. Multi-image grouping for side-by-side diagrams

Tuned for NCERT textbooks (single-column, "Figure X.Y" captions, vertical
dominance).
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

# Image extraction thresholds
MIN_IMAGE_DIMENSION = 50   # px – skip images narrower/shorter than this
MIN_IMAGE_AREA = 5000      # px² – skip tiny decorative images

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────

# Maximum vertical pixel gap to consider a text block "near" an image
CAPTION_VERTICAL_GAP = 40      # px — caption immediately below image
CONTEXT_VERTICAL_GAP = 120     # px — explanatory paragraph above / below
QUESTION_VERTICAL_GAP = 200    # px — questions referencing the image

# Horizontal overlap threshold — fraction of width that must overlap
HORIZONTAL_OVERLAP_THRESHOLD = 0.3

# Side-by-side grouping — Y-range overlap fraction for image grouping
GROUP_Y_OVERLAP_THRESHOLD = 0.5

# ─────────────────────────────────────────────────────────────────────
# Patterns (NCERT-specific)
# ─────────────────────────────────────────────────────────────────────

_RE_FIGURE_CAPTION = re.compile(
    r"^(?:figure|fig\.?)\s*(\d+(?:\.\d+)*)\s*[:\-\u2013\u2014.]?\s*(.*)",
    re.IGNORECASE,
)

_RE_QUESTION_CUE = re.compile(
    r"(?:look\s+at\s+figure|refer\s+to\s+fig|observe\s+fig|answer|"
    r"what\s+does|explain|describe|identify|label|draw|name\s+the)",
    re.IGNORECASE,
)

_RE_HEADING = re.compile(
    r"^(?:chapter\s+\d+|(?:\d+\.)+\d*)\s*[:\-\u2013\u2014]?\s*(.+)?$",
    re.IGNORECASE,
)

_RE_ALLCAPS_HEADING = re.compile(r"^[A-Z][A-Z\s\-:,]{4,}$")


# ─────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────

class BlockRole(Enum):
    """Role assigned to a text block after classification."""
    HEADING = auto()
    CAPTION = auto()
    CONTEXT = auto()
    QUESTION = auto()
    BODY = auto()


@dataclass
class BBox:
    """Axis-aligned bounding box (page coordinates, origin = top-left)."""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0

    def horizontal_overlap(self, other: BBox) -> float:
        """Return fraction of the narrower block's width that overlaps."""
        overlap = max(0, min(self.x1, other.x1) - max(self.x0, other.x0))
        narrower = min(self.width, other.width)
        return overlap / narrower if narrower > 0 else 0.0

    def vertical_distance(self, other: BBox) -> float:
        """Signed vertical gap: positive = *other* is below *self*."""
        if other.y0 >= self.y1:
            return other.y0 - self.y1
        if self.y0 >= other.y1:
            return -(self.y0 - other.y1)
        return 0.0  # overlapping vertically

    def y_overlap_fraction(self, other: BBox) -> float:
        """Fraction of the shorter block's height that overlaps in Y."""
        overlap = max(0, min(self.y1, other.y1) - max(self.y0, other.y0))
        shorter = min(self.height, other.height)
        return overlap / shorter if shorter > 0 else 0.0

    @classmethod
    def from_fitz(cls, rect: fitz.Rect) -> BBox:
        return cls(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1)


@dataclass
class TextBlock:
    """A positioned text block extracted from a single page."""
    text: str
    bbox: BBox
    page: int
    role: BlockRole = BlockRole.BODY
    section_title: Optional[str] = None


@dataclass
class ImageBlock:
    """A positioned image extracted from a single page."""
    image_bytes: bytes          # PNG data (empty until rendering)
    bbox: BBox
    page: int
    figure_id: Optional[str] = None   # e.g. "1.1"
    caption: Optional[str] = None
    content_hash: str = ""
    # Original rect for deferred rendering (crop before render)
    source_rect: Optional[fitz.Rect] = field(default=None, repr=False)


@dataclass
class ImageGroup:
    """Side-by-side images that form one semantic unit."""
    images: List[ImageBlock] = field(default_factory=list)
    bbox: Optional[BBox] = None       # bounding box covering all images

    def compute_bbox(self) -> None:
        if not self.images:
            return
        self.bbox = BBox(
            x0=min(im.bbox.x0 for im in self.images),
            y0=min(im.bbox.y0 for im in self.images),
            x1=max(im.bbox.x1 for im in self.images),
            y1=max(im.bbox.y1 for im in self.images),
        )


@dataclass
class VisualChunk:
    """Final output — a chunk enriched with spatially-linked images.

    Maps directly to ``core.chunks`` + ``core.images`` +
    ``core.chunk_image_links`` in schema.sql.
    """
    content: str
    section_title: Optional[str] = None
    position_index: int = 0
    role: BlockRole = BlockRole.BODY
    page: int = 0

    # Linked images (to be stored in core.images & core.chunk_image_links)
    images: List[ImageBlock] = field(default_factory=list)

    # Caption + context + question blocks merged into the chunk
    caption: Optional[str] = None
    context: Optional[str] = None
    questions: List[str] = field(default_factory=list)

    def full_content(self) -> str:
        """Content enriched with structural metadata for embedding."""
        parts: List[str] = []
        if self.section_title:
            parts.append(f"[{self.section_title}]")
        parts.append(self.content)
        if self.caption:
            parts.append(f"Caption: {self.caption}")
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.questions:
            parts.append("Questions: " + " | ".join(self.questions))
        return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _content_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _is_blank_pixmap(pix: fitz.Pixmap) -> bool:
    """True if every sampled pixel has the same colour (solid fill)."""
    samples = pix.samples
    bpp = pix.n
    if len(samples) < bpp:
        return True
    first = samples[:bpp]
    stride = max(bpp, bpp * 64)
    for offset in range(0, len(samples), stride):
        if samples[offset : offset + bpp] != first:
            return False
    return True


def _classify_text(text: str) -> BlockRole:
    """Quick heuristic role for a text block."""
    stripped = text.strip()
    if not stripped:
        return BlockRole.BODY

    if _RE_FIGURE_CAPTION.match(stripped):
        return BlockRole.CAPTION

    word_count = len(stripped.split())
    if _RE_HEADING.match(stripped):
        return BlockRole.HEADING
    if _RE_ALLCAPS_HEADING.match(stripped) and word_count <= 10:
        return BlockRole.HEADING
    if word_count <= 8 and stripped.istitle() and not stripped.endswith("."):
        return BlockRole.HEADING

    if _RE_QUESTION_CUE.search(stripped):
        return BlockRole.QUESTION

    return BlockRole.BODY


def _parse_caption(text: str) -> Tuple[Optional[str], str]:
    """Extract figure ID and caption text from a caption line.

    Returns ``(figure_id, caption_text)`` or ``(None, original)`` if not a
    figure caption.
    """
    m = _RE_FIGURE_CAPTION.match(text.strip())
    if m:
        fig_id = m.group(1)
        cap = m.group(2).strip().rstrip(".")
        return fig_id, cap
    return None, text.strip()


# ─────────────────────────────────────────────────────────────────────
# Step 1 + 2 + 3 — Extract images & text blocks with bboxes
# ─────────────────────────────────────────────────────────────────────

def extract_page_elements(
    doc: fitz.Document,
) -> Tuple[List[TextBlock], List[ImageBlock]]:
    """Walk every page and extract positioned text blocks & images."""
    all_texts: List[TextBlock] = []
    all_images: List[ImageBlock] = []
    seen_hashes: Dict[str, bool] = {}

    for page in doc:
        page_num = page.number

        # ── Text blocks (dict mode = layout aware) ──────────────────
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for blk in blocks:
            if blk["type"] != 0:  # 0 = text block
                continue

            # Reassemble lines into a single text string
            lines: List[str] = []
            for line in blk.get("lines", []):
                span_text = "".join(span["text"] for span in line.get("spans", []))
                if span_text.strip():
                    lines.append(span_text.strip())

            text = "\n".join(lines)
            if not text.strip():
                continue

            bbox = BBox(
                x0=blk["bbox"][0],
                y0=blk["bbox"][1],
                x1=blk["bbox"][2],
                y1=blk["bbox"][3],
            )
            role = _classify_text(text)
            all_texts.append(
                TextBlock(text=text, bbox=bbox, page=page_num, role=role)
            )

        # ── Images (collect rects only — rendering deferred) ────────
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                rect = rects[0]

                if rect.width < MIN_IMAGE_DIMENSION or rect.height < MIN_IMAGE_DIMENSION:
                    continue
                if rect.width * rect.height < MIN_IMAGE_AREA:
                    continue

                all_images.append(
                    ImageBlock(
                        image_bytes=b"",  # rendered later after crop
                        bbox=BBox.from_fitz(rect),
                        page=page_num,
                        source_rect=rect,
                    )
                )
            except Exception:
                logger.debug("Could not extract image xref=%d on page %d", xref, page_num)

    return all_texts, all_images


# ─────────────────────────────────────────────────────────────────────
# Step 4 — Spatial association
# ─────────────────────────────────────────────────────────────────────

def _find_nearest_text(
    image: ImageBlock,
    texts: List[TextBlock],
    role_filter: Optional[BlockRole] = None,
    max_gap: float = CONTEXT_VERTICAL_GAP,
) -> List[TextBlock]:
    """Return text blocks on the same page near *image*, sorted by distance.

    Filters by role if specified.  Requires horizontal overlap above
    ``HORIZONTAL_OVERLAP_THRESHOLD`` and vertical gap ≤ ``max_gap``.
    """
    candidates: List[Tuple[float, TextBlock]] = []
    for tb in texts:
        if tb.page != image.page:
            continue
        if role_filter is not None and tb.role != role_filter:
            continue
        if image.bbox.horizontal_overlap(tb.bbox) < HORIZONTAL_OVERLAP_THRESHOLD:
            continue
        vdist = abs(image.bbox.vertical_distance(tb.bbox))
        if vdist <= max_gap:
            candidates.append((vdist, tb))

    candidates.sort(key=lambda x: x[0])
    return [tb for _, tb in candidates]


def associate_images(
    texts: List[TextBlock],
    images: List[ImageBlock],
    doc: fitz.Document,
) -> List[ImageBlock]:
    """Attach caption, figure_id to each image, then render.

    Images are cropped to end at the caption's top edge so that body
    text below the caption is never included in the rendered PNG.
    Uncaptioned images (decorative elements) are dropped entirely.

    Mutates ``ImageBlock`` objects in-place and returns the filtered list.
    """
    caption_blocks: Dict[int, TextBlock] = {}  # img index → caption block

    for idx, img in enumerate(images):
        # 1. Caption — closest caption-role block below image
        caption_candidates = _find_nearest_text(
            img, texts, role_filter=BlockRole.CAPTION, max_gap=CAPTION_VERTICAL_GAP,
        )
        # Also check blocks immediately below even if not pre-classified
        if not caption_candidates:
            below_blocks = [
                tb for tb in texts
                if tb.page == img.page
                and img.bbox.horizontal_overlap(tb.bbox) >= HORIZONTAL_OVERLAP_THRESHOLD
                and 0 < img.bbox.vertical_distance(tb.bbox) <= CAPTION_VERTICAL_GAP
            ]
            below_blocks.sort(key=lambda tb: img.bbox.vertical_distance(tb.bbox))
            for tb in below_blocks:
                fig_id, cap = _parse_caption(tb.text)
                if fig_id:
                    caption_candidates = [tb]
                    break

        if caption_candidates:
            cap_block = caption_candidates[0]
            fig_id, cap_text = _parse_caption(cap_block.text)
            img.figure_id = fig_id
            img.caption = cap_text if cap_text else cap_block.text.strip()
            cap_block.role = BlockRole.CAPTION  # mark consumed
            caption_blocks[idx] = cap_block

    # ── Drop uncaptioned images ─────────────────────────────────────
    before = len(images)
    keep_indices = [i for i, img in enumerate(images) if img.figure_id is not None]
    dropped = before - len(keep_indices)
    if dropped:
        logger.info(
            "Dropped %d uncaptioned images (decorative / portraits)", dropped
        )

    # ── Render surviving images, cropped above caption ──────────────
    seen_hashes: Dict[str, bool] = {}
    rendered: List[ImageBlock] = []

    for idx in keep_indices:
        img = images[idx]
        if img.source_rect is None:
            continue

        page = doc[img.page]
        clip = fitz.Rect(img.source_rect)  # copy

        # Crop: if we found a caption, end the image at the caption's
        # top edge so no text below the caption leaks into the PNG.
        cap_block = caption_blocks.get(idx)
        if cap_block is not None:
            clip.y1 = min(clip.y1, cap_block.bbox.y0)

        # Safety: skip if crop made the rect degenerate
        if clip.width < MIN_IMAGE_DIMENSION or clip.height < MIN_IMAGE_DIMENSION:
            continue

        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(clip=clip, matrix=mat, alpha=False)

        if _is_blank_pixmap(pix):
            continue

        png_bytes = pix.tobytes("png")
        h = _content_hash(png_bytes)
        if h in seen_hashes:
            continue
        seen_hashes[h] = True

        img.image_bytes = png_bytes
        img.content_hash = h
        img.bbox = BBox.from_fitz(clip)  # update bbox to cropped region
        rendered.append(img)

    return rendered


# ─────────────────────────────────────────────────────────────────────
# Step 5 — Multi-image grouping
# ─────────────────────────────────────────────────────────────────────

def group_side_by_side(images: List[ImageBlock]) -> List[ImageGroup]:
    """Group images on the same page that share a similar Y-range.

    Two images are grouped if their vertical overlap fraction exceeds
    ``GROUP_Y_OVERLAP_THRESHOLD`` — this catches side-by-side diagrams in
    NCERT textbooks that form a single semantic unit.
    """
    if not images:
        return []

    # Sort by page then x-position
    sorted_imgs = sorted(images, key=lambda im: (im.page, im.bbox.x0))

    groups: List[ImageGroup] = []
    used = set()

    for i, img in enumerate(sorted_imgs):
        if i in used:
            continue
        group = ImageGroup(images=[img])
        used.add(i)

        for j in range(i + 1, len(sorted_imgs)):
            if j in used:
                continue
            other = sorted_imgs[j]
            if other.page != img.page:
                break  # different page, stop

            # Check Y-overlap
            if img.bbox.y_overlap_fraction(other.bbox) >= GROUP_Y_OVERLAP_THRESHOLD:
                group.images.append(other)
                used.add(j)

        group.compute_bbox()
        groups.append(group)

    return groups


# ─────────────────────────────────────────────────────────────────────
# Build final chunks — assemble text + images
# ─────────────────────────────────────────────────────────────────────

def build_visual_chunks(
    texts: List[TextBlock],
    images: List[ImageBlock],
) -> List[VisualChunk]:
    """Assemble ``VisualChunk`` objects from extracted text & image blocks.

    Each body / heading text block becomes a chunk.  Images are linked to
    the nearest chunk via spatial proximity.  Caption and question blocks
    are folded into the image's parent chunk rather than becoming standalone
    chunks.

    Returns chunks sorted by ``(page, y-position)`` with ``position_index``
    assigned sequentially — matching ``core.chunks.position_index`` in the
    schema.
    """
    # Track current section title (from headings)
    current_section: Optional[str] = None
    # Collect raw chunks (unlinked to images yet)
    raw_chunks: List[VisualChunk] = []

    # Sort text blocks by reading order (page → y → x)
    ordered_texts = sorted(texts, key=lambda tb: (tb.page, tb.bbox.y0, tb.bbox.x0))

    for tb in ordered_texts:
        if tb.role == BlockRole.HEADING:
            current_section = tb.text.strip()
            continue

        if tb.role == BlockRole.CAPTION:
            # Captions will be attached to image chunks; skip standalone
            continue

        chunk = VisualChunk(
            content=tb.text.strip(),
            section_title=current_section,
            page=tb.page,
            role=tb.role,
        )

        # If this is a question block, stash it
        if tb.role == BlockRole.QUESTION:
            chunk.questions = [tb.text.strip()]

        raw_chunks.append(chunk)

    # ── Link images to their nearest chunk ──────────────────────────
    # For each image, find the closest BODY/CONTEXT chunk on the same
    # page (preferring the paragraph above, then below).

    image_groups = group_side_by_side(images)

    for group in image_groups:
        # Use the group's combined bbox for proximity
        ref_bbox = group.bbox or group.images[0].bbox
        ref_page = group.images[0].page

        # Find nearest body chunk
        best_chunk: Optional[VisualChunk] = None
        best_dist = float("inf")

        for chunk in raw_chunks:
            if chunk.page != ref_page:
                continue
            if chunk.role not in (BlockRole.BODY, BlockRole.CONTEXT):
                continue

            # Approximate the chunk's bbox from its text block position
            # We don't have bbox on VisualChunk, so search the original
            # text blocks for a match
            for tb in ordered_texts:
                if tb.text.strip() == chunk.content and tb.page == ref_page:
                    h_overlap = ref_bbox.horizontal_overlap(tb.bbox)
                    if h_overlap < HORIZONTAL_OVERLAP_THRESHOLD:
                        continue
                    vdist = abs(ref_bbox.vertical_distance(tb.bbox))
                    if vdist < best_dist:
                        best_dist = vdist
                        best_chunk = chunk
                    break

        if best_chunk is not None:
            best_chunk.images.extend(group.images)
            # Attach caption from the first captioned image
            for im in group.images:
                if im.caption and not best_chunk.caption:
                    best_chunk.caption = im.caption
        else:
            # No nearby text — create a standalone image chunk
            caption_parts = []
            for im in group.images:
                label = f"Figure {im.figure_id}" if im.figure_id else "Figure"
                if im.caption:
                    label += f": {im.caption}"
                caption_parts.append(label)

            raw_chunks.append(
                VisualChunk(
                    content="\n".join(caption_parts),
                    section_title=current_section,
                    page=ref_page,
                    role=BlockRole.CAPTION,
                    images=list(group.images),
                    caption=caption_parts[0] if caption_parts else None,
                )
            )

    # ── Fold question blocks into the nearest prior body chunk ──────
    merged: List[VisualChunk] = []
    for chunk in raw_chunks:
        if chunk.role == BlockRole.QUESTION and merged:
            # Attach to the last body chunk
            for prev in reversed(merged):
                if prev.role in (BlockRole.BODY, BlockRole.CONTEXT, BlockRole.CAPTION):
                    prev.questions.extend(chunk.questions)
                    break
            else:
                merged.append(chunk)
        else:
            merged.append(chunk)

    # ── Assign position_index in reading order ──────────────────────
    merged.sort(key=lambda c: (c.page, c.role != BlockRole.BODY))
    for idx, chunk in enumerate(merged):
        chunk.position_index = idx

    return merged


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def parse_pdf_visual(pdf_path: str) -> List[VisualChunk]:
    """Parse a PDF with full layout awareness and return ``VisualChunk`` list.

    This is the main entry point.  Each ``VisualChunk`` contains:
    - ``content``       — text body
    - ``section_title`` — heading breadcrumb
    - ``position_index``— ordering for ``core.chunks``
    - ``images``        — linked ``ImageBlock`` list (for ``core.images``
                          + ``core.chunk_image_links``)
    - ``caption``       — detected figure caption
    - ``questions``     — nearby question text
    """
    doc = fitz.open(pdf_path)
    try:
        texts, images = extract_page_elements(doc)
        images = associate_images(texts, images, doc)
        chunks = build_visual_chunks(texts, images)
    finally:
        doc.close()

    logger.info(
        "VisualParser: %d chunks (%d with images) from %s",
        len(chunks),
        sum(1 for c in chunks if c.images),
        pdf_path,
    )
    return chunks