"""Structure-aware PDF extraction and NLP-based semantic chunking.

Tuned for textbooks like NCERT that follow predictable structural patterns:
numbered sections, definition boxes, examples, activities, summaries, etc.

Uses PyMuPDF for extraction and spaCy for sentence segmentation.  Produces
*structural nodes* – chunks that carry their heading / section context so
downstream consumers know *where* in the book the content came from.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import fitz
import spacy

from Core.Embedder.constants import (
    MAX_CHUNK_WORDS,
    MIN_CHUNK_CHARS,
    MIN_IMAGE_AREA,
    MIN_IMAGE_DIMENSION,
    SPACY_MODEL,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Lazy-loaded spaCy model
# ──────────────────────────────────────────────────────────────────────

_nlp: spacy.language.Language | None = None


def _get_nlp() -> spacy.language.Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load(SPACY_MODEL)
    return _nlp


# ──────────────────────────────────────────────────────────────────────
# Structural patterns (NCERT / general textbook)
# ──────────────────────────────────────────────────────────────────────

# Numbered sections: "1.1", "1.2.3", "Chapter 1", "CHAPTER 1"
_RE_NUMBERED_HEADING = re.compile(
    r"^(?:chapter\s+\d+|(?:\d+\.)+\d*)\s*[:\-–—]?\s*(.+)?$",
    re.IGNORECASE,
)

# ALL-CAPS short lines (≤ 10 words) → likely a heading
_RE_ALLCAPS_HEADING = re.compile(r"^[A-Z][A-Z\s\-:,]{4,}$")

# NCERT-specific markers
_RE_DEFINITION = re.compile(r"^\s*(definition|define)\s*[:\-–—]", re.IGNORECASE)
_RE_EXAMPLE = re.compile(r"^\s*(example|solved\s+example|illustration)\s*[\d.:–\-]", re.IGNORECASE)
_RE_ACTIVITY = re.compile(r"^\s*(activity|experiment|do\s+you\s+know|think\s+about\s+it)\s*[:\-–—\d.]", re.IGNORECASE)
_RE_SUMMARY = re.compile(r"^\s*(summary|points?\s+to\s+remember|key\s+points?|recap)\s*$", re.IGNORECASE)
_RE_QUESTION = re.compile(r"^\s*(exercises?|questions?|problems?|intext\s+questions?)\s*$", re.IGNORECASE)

# Bullet / numbered list items
_RE_LIST_ITEM = re.compile(r"^\s*(?:[•●▪▸\-\*]|\(?[a-zA-Z0-9ivx]+[).])\s+")


# ──────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────

@dataclass
class StructuralNode:
    """A parsed chunk enriched with structural context."""

    content: str
    heading: Optional[str] = None
    section_path: List[str] = field(default_factory=list)

    def context_prefix(self) -> str:
        """Return a human-readable breadcrumb like ``'1.1 Motion > Definition'``."""
        parts = [p for p in self.section_path if p]
        if self.heading and self.heading not in parts:
            parts.append(self.heading)
        return " > ".join(parts) if parts else ""

    def full_content(self) -> str:
        """Content prefixed with structural breadcrumb for richer embeddings."""
        prefix = self.context_prefix()
        if prefix:
            return f"[{prefix}]\n{self.content}"
        return self.content


# ──────────────────────────────────────────────────────────────────────
# PDF Extraction — robust image handling
# ──────────────────────────────────────────────────────────────────────

def _is_blank_image(pix: fitz.Pixmap) -> bool:
    """Return True if every pixel in *pix* has the same colour (solid fill)."""
    samples = pix.samples  # raw bytes
    bpp = pix.n             # bytes per pixel
    if len(samples) < bpp:
        return True
    first_pixel = samples[:bpp]
    # Check a strided subset for speed (every 64th pixel)
    stride = max(bpp, bpp * 64)
    for offset in range(0, len(samples), stride):
        if samples[offset : offset + bpp] != first_pixel:
            return False
    return True


def _content_hash(data: bytes) -> str:
    """Fast content hash for deduplication."""
    return hashlib.md5(data).hexdigest()


def extract_pdf(pdf_path: str) -> Tuple[str, List[bytes]]:
    """Extract plain text and meaningful raster images from a PDF.

    Returns ``(full_text, [image_bytes_png, ...])``.

    Image extraction renders each image *from the page* rather than pulling
    raw xref data.  This guarantees correct colourspace, SMask compositing,
    and alpha handling — fixing the "black screen" bug.
    """
    doc = fitz.open(pdf_path)
    text_parts: List[str] = []
    images: List[bytes] = []
    seen_hashes: Dict[str, bool] = {}

    for page in doc:
        text_parts.append(page.get_text("text"))

        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                # Get the rectangle(s) where this image is placed on the page
                rects = page.get_image_rects(xref)
                if not rects:
                    continue

                rect = rects[0]  # use the first placement

                # Skip tiny / decorative images
                width = rect.width
                height = rect.height
                if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                    continue
                if width * height < MIN_IMAGE_AREA:
                    continue

                # Render from the page (respects SMask, colorspace, transforms)
                # Use a 2x scale matrix for decent quality
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(clip=rect, matrix=mat, alpha=False)

                # Skip solid-colour images (blank / black fills)
                if _is_blank_image(pix):
                    logger.debug(
                        "Skipping blank image xref=%d on page %d", xref, page.number
                    )
                    continue

                png_bytes = pix.tobytes("png")

                # Deduplicate by content hash
                h = _content_hash(png_bytes)
                if h in seen_hashes:
                    continue
                seen_hashes[h] = True

                images.append(png_bytes)
                logger.debug(
                    "Extracted image xref=%d page=%d size=%dx%d (%d bytes)",
                    xref, page.number, pix.width, pix.height, len(png_bytes),
                )
            except Exception:
                logger.debug("Could not extract image xref=%d", xref)

    doc.close()
    return "\n".join(text_parts), images


# ──────────────────────────────────────────────────────────────────────
# Line-level classification
# ──────────────────────────────────────────────────────────────────────

def _is_heading(line: str) -> bool:
    """Heuristic: line is a heading if it matches structural patterns."""
    stripped = line.strip()
    if not stripped:
        return False
    word_count = len(stripped.split())
    if _RE_NUMBERED_HEADING.match(stripped):
        return True
    if _RE_ALLCAPS_HEADING.match(stripped) and word_count <= 10:
        return True
    # Title-case short line (≤ 8 words, no trailing period)
    if word_count <= 8 and stripped.istitle() and not stripped.endswith("."):
        return True
    return False


# ──────────────────────────────────────────────────────────────────────
# Structure-Aware Chunking
# ──────────────────────────────────────────────────────────────────────

def split_into_chunks(text: str) -> List[StructuralNode]:
    """Parse raw text into ``StructuralNode`` objects using structural cues.

    Strategy
    --------
    1. Walk lines top-to-bottom, tracking the current section path (heading
       hierarchy) like a stack.
    2. When a heading is detected, flush the current chunk and update the
       section context.
    3. Within a section, sentences are grouped into chunks respecting
       ``MAX_CHUNK_WORDS`` using spaCy for proper sentence boundaries.
    4. Drops chunks shorter than ``MIN_CHUNK_CHARS``.
    """
    nlp = _get_nlp()
    lines = text.split("\n")
    nodes: List[StructuralNode] = []

    # Running state
    section_stack: List[str] = []
    current_heading: Optional[str] = None
    buffer: List[str] = []

    def _flush() -> None:
        """Convert buffered lines into one or more StructuralNodes."""
        nonlocal buffer
        raw = "\n".join(buffer).strip()
        buffer = []
        if len(raw) < MIN_CHUNK_CHARS:
            return

        word_count = len(raw.split())
        if word_count <= MAX_CHUNK_WORDS:
            nodes.append(
                StructuralNode(
                    content=raw,
                    heading=current_heading,
                    section_path=list(section_stack),
                )
            )
            return

        # Oversized block → split at sentence boundaries via spaCy
        doc = nlp(raw)
        current_sents: List[str] = []
        current_wc = 0

        for sent in doc.sents:
            sent_text = sent.text.strip()
            if not sent_text:
                continue
            s_wc = len(sent_text.split())

            if current_wc + s_wc > MAX_CHUNK_WORDS and current_sents:
                chunk_text = " ".join(current_sents)
                if len(chunk_text) >= MIN_CHUNK_CHARS:
                    nodes.append(
                        StructuralNode(
                            content=chunk_text,
                            heading=current_heading,
                            section_path=list(section_stack),
                        )
                    )
                current_sents = []
                current_wc = 0

            current_sents.append(sent_text)
            current_wc += s_wc

        if current_sents:
            chunk_text = " ".join(current_sents)
            if len(chunk_text) >= MIN_CHUNK_CHARS:
                nodes.append(
                    StructuralNode(
                        content=chunk_text,
                        heading=current_heading,
                        section_path=list(section_stack),
                    )
                )

    # ── Main line-by-line walk ──────────────────────────────────────

    for line in lines:
        stripped = line.strip()

        # Skip blank lines (but allow them inside a buffer for paragraph feel)
        if not stripped:
            if buffer:
                buffer.append("")
            continue

        # Check for heading
        if _is_heading(stripped):
            _flush()

            # Maintain a simple section stack based on numbered depth
            num_match = _RE_NUMBERED_HEADING.match(stripped)
            if num_match:
                # Depth = number of dots + 1  (e.g. "1.2" → depth 2)
                depth = stripped.split()[0].count(".") + 1
                section_stack = section_stack[: depth - 1]
                section_stack.append(stripped)
            else:
                # Non-numbered heading → keep existing stack, push on top
                section_stack.append(stripped)

            current_heading = stripped
            continue

        buffer.append(stripped)

    # Final flush
    _flush()

    return nodes
