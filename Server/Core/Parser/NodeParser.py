"""Text-side PDF parser — produces chunks and figure references.

Complements ``VisualParser`` (which extracts images) by handling
the **text** pipeline:

1. Extract text from PDF with layout awareness (PyMuPDF)
2. Detect section headings (NCERT numbered + ALL-CAPS patterns)
3. Split into semantic chunks at sentence boundaries (spaCy)
4. Extract and deduplicate figure references (``Fig 1.1``, ``Figure 2``)
5. Return ``[chunks, image_refs]`` ready for DB insertion

Schema alignment (schema.sql)
-----------------------------
- ``core.chunks``  → content, token_count, position_index, section_title
- ``core.chunk_image_links`` → via image_refs (mapped downstream)
"""

from __future__ import annotations

import logging
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import fitz
import spacy

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Constants (duplicated from Embedder.constants to avoid circular import)
# ─────────────────────────────────────────────────────────────────────

MIN_CHUNK_CHARS = 20
MAX_CHUNK_WORDS = 550
SPACY_MODEL = "en_core_web_sm"

# ─────────────────────────────────────────────────────────────────────
# Lazy-loaded spaCy model
# ─────────────────────────────────────────────────────────────────────

_nlp: spacy.language.Language | None = None


def _get_nlp() -> spacy.language.Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load(SPACY_MODEL)
    return _nlp


# ─────────────────────────────────────────────────────────────────────
# Patterns (NCERT / general textbook)
# ─────────────────────────────────────────────────────────────────────

# Numbered sections: "1.1", "1.2.3", "Chapter 1"
_RE_NUMBERED_HEADING = re.compile(
    r"^(?:chapter\s+\d+|(?:\d+\.)+\d*)\s*[:\-\u2013\u2014]?\s*(.+)?$",
    re.IGNORECASE,
)

# ALL-CAPS short lines (≤ 10 words)
_RE_ALLCAPS_HEADING = re.compile(r"^[A-Z][A-Z\s\-:,]{4,}$")

# NCERT figure captions (standalone lines)
_RE_FIGURE_CAPTION = re.compile(
    r"^(?:figure|fig\.?)\s*(\d+(?:\.\d+)*)\s*[:\-\u2013\u2014.]?\s*(.*)",
    re.IGNORECASE,
)

# Figure references embedded in body text (inline)
# Matches: Fig 1.1, Figure 2, Fig. 3.2 Map Types
_RE_FIG_REF = re.compile(
    r"(Fig(?:ure)?\.?\s*\d+(?:\.\d+)?)(\s*[:\-]?\s*[A-Za-z].*?)?(?=[,;.\)\]\s]|$)",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────

@dataclass
class TextChunk:
    """A parsed text chunk ready for ``core.chunks``.

    Fields map directly to schema columns:
    - content        → core.chunks.content
    - token_count    → core.chunks.token_count (approx word count)
    - position_index → core.chunks.position_index
    - section_title  → core.chunks.section_title
    """
    content: str
    token_count: int = 0
    position_index: int = 0
    section_title: Optional[str] = None
    section_path: List[str] = field(default_factory=list)

    # Figure references found within this chunk (for chunk_image_links)
    figure_refs: List[str] = field(default_factory=list)

    def full_content(self) -> str:
        """Content prefixed with structural breadcrumb for embeddings."""
        prefix = " > ".join(p for p in self.section_path if p)
        if self.section_title and self.section_title not in (self.section_path or []):
            prefix = f"{prefix} > {self.section_title}" if prefix else self.section_title
        if prefix:
            return f"[{prefix}]\n{self.content}"
        return self.content


@dataclass
class ImageRef:
    """A deduplicated figure reference extracted from text.

    Used downstream to populate ``core.chunk_image_links`` by matching
    ``ref_id`` (e.g. ``"1.1"``) against ``core.images.figure_id``.
    """
    ref_id: str       # e.g. "1.1", "2", "3.2"
    title: str        # e.g. "Watershed Transformation" (may be empty)
    display: str      # e.g. "Fig 1.1 Watershed Transformation"


# ─────────────────────────────────────────────────────────────────────
# Heading detection
# ─────────────────────────────────────────────────────────────────────

def _is_heading(line: str) -> bool:
    """Heuristic: line is a section heading."""
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


# ─────────────────────────────────────────────────────────────────────
# Step 1: Extract figure references from text
# ─────────────────────────────────────────────────────────────────────

def _extract_refs_from_text(text: str) -> List[ImageRef]:
    """Scan text for figure references and return deduplicated list.

    Matches patterns like:
    - ``Fig 1.1``
    - ``Figure 2``
    - ``Fig. 3.2 Map Types``

    Returns references in appearance order, deduplicated by ref_id.
    """
    seen: OrderedDict[str, ImageRef] = OrderedDict()

    for m in _RE_FIG_REF.finditer(text):
        ref_part = m.group(1).strip()          # "Fig 1.1"
        title_part = (m.group(2) or "").strip() # "Map Types"
        # Strip leading punctuation from title
        title_part = re.sub(r"^[:\-\u2013\u2014.\s]+", "", title_part).strip()

        # Normalise ref_id: extract just the number
        num_match = re.search(r"(\d+(?:\.\d+)*)", ref_part)
        if not num_match:
            continue
        ref_id = num_match.group(1)  # e.g. "1.1"

        if ref_id in seen:
            # Update title if this occurrence has one and previous didn't
            if title_part and not seen[ref_id].title:
                seen[ref_id] = ImageRef(
                    ref_id=ref_id,
                    title=title_part,
                    display=f"Fig {ref_id} {title_part}",
                )
            continue

        display = f"Fig {ref_id} {title_part}".strip() if title_part else f"Fig {ref_id}"
        seen[ref_id] = ImageRef(ref_id=ref_id, title=title_part, display=display)

    return list(seen.values())


def _extract_refs_from_chunk(text: str) -> List[str]:
    """Return list of figure ref_ids mentioned in a chunk's text."""
    refs: List[str] = []
    for m in _RE_FIG_REF.finditer(text):
        num_match = re.search(r"(\d+(?:\.\d+)*)", m.group(1))
        if num_match:
            ref_id = num_match.group(1)
            if ref_id not in refs:
                refs.append(ref_id)
    return refs


# ─────────────────────────────────────────────────────────────────────
# Step 2: Structure-aware text chunking
# ─────────────────────────────────────────────────────────────────────

def _chunk_text(text: str) -> Tuple[List[TextChunk], List[ImageRef]]:
    """Parse raw text into ``TextChunk`` and ``ImageRef`` objects.

    Strategy:
    1. Walk lines top-to-bottom, tracking the heading hierarchy.
    2. Flush the buffer at heading boundaries.
    3. Figure captions are extracted and excluded from chunks.
    4. Oversized sections are split at spaCy sentence boundaries.
    5. Figure references within each chunk are recorded.
    """
    nlp = _get_nlp()
    lines = text.split("\n")
    chunks: List[TextChunk] = []

    # Running state
    section_stack: List[str] = []
    current_heading: Optional[str] = None
    buffer: List[str] = []

    def _flush() -> None:
        """Convert buffered lines into one or more TextChunks."""
        nonlocal buffer
        raw = "\n".join(buffer).strip()
        buffer = []
        if len(raw) < MIN_CHUNK_CHARS:
            return

        word_count = len(raw.split())
        if word_count <= MAX_CHUNK_WORDS:
            chunk = TextChunk(
                content=raw,
                token_count=word_count,
                section_title=current_heading,
                section_path=list(section_stack),
                figure_refs=_extract_refs_from_chunk(raw),
            )
            chunks.append(chunk)
            return

        # Oversized → split at sentence boundaries via spaCy
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
                    chunks.append(TextChunk(
                        content=chunk_text,
                        token_count=len(chunk_text.split()),
                        section_title=current_heading,
                        section_path=list(section_stack),
                        figure_refs=_extract_refs_from_chunk(chunk_text),
                    ))
                current_sents = []
                current_wc = 0

            current_sents.append(sent_text)
            current_wc += s_wc

        if current_sents:
            chunk_text = " ".join(current_sents)
            if len(chunk_text) >= MIN_CHUNK_CHARS:
                chunks.append(TextChunk(
                    content=chunk_text,
                    token_count=len(chunk_text.split()),
                    section_title=current_heading,
                    section_path=list(section_stack),
                    figure_refs=_extract_refs_from_chunk(chunk_text),
                ))

    # ── Main line-by-line walk ──────────────────────────────────────

    for line in lines:
        stripped = line.strip()

        # Skip blank lines (preserve paragraph structure in buffer)
        if not stripped:
            if buffer:
                buffer.append("")
            continue

        # Figure captions → extract but don't include in chunks
        fig_match = _RE_FIGURE_CAPTION.match(stripped)
        if fig_match:
            _flush()
            continue

        # Heading detection
        if _is_heading(stripped):
            _flush()

            # Maintain section stack based on numbered depth
            num_match = _RE_NUMBERED_HEADING.match(stripped)
            if num_match:
                depth = stripped.split()[0].count(".") + 1
                section_stack = section_stack[: depth - 1]
                section_stack.append(stripped)
            else:
                section_stack.append(stripped)

            current_heading = stripped
            continue

        buffer.append(stripped)

    # Final flush
    _flush()

    # ── Assign position_index ───────────────────────────────────────
    for idx, chunk in enumerate(chunks):
        chunk.position_index = idx

    # ── Extract all image references from full text ─────────────────
    all_refs = _extract_refs_from_text(text)

    return chunks, all_refs


# ─────────────────────────────────────────────────────────────────────
# Step 3: PDF extraction (layout-aware)
# ─────────────────────────────────────────────────────────────────────

def _extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from a PDF using PyMuPDF layout-aware mode."""
    doc = fitz.open(pdf_path)
    pages: List[str] = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages)


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def parse_pdf_text(pdf_path: str) -> Tuple[List[TextChunk], List[ImageRef]]:
    """Parse a PDF and return ``(chunks, image_refs)``.

    This is the main entry point for the text pipeline.

    Returns
    -------
    chunks : list[TextChunk]
        Structured text chunks for ``core.chunks``.  Each chunk carries:
        - ``content`` / ``token_count`` / ``position_index`` / ``section_title``
        - ``figure_refs`` — list of figure IDs referenced in the chunk
          (for building ``core.chunk_image_links``)

    image_refs : list[ImageRef]
        Deduplicated, ordered list of all figure references found in the
        PDF.  Each entry has ``ref_id``, ``title``, and ``display`` fields.
    """
    raw_text = _extract_text_from_pdf(pdf_path)
    chunks, image_refs = _chunk_text(raw_text)

    logger.info(
        "NodeParser: %d chunks, %d unique figure references from %s",
        len(chunks),
        len(image_refs),
        pdf_path,
    )
    return chunks, image_refs