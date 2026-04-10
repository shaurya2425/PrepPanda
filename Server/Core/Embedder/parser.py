"""Structure-aware PDF extraction and NLP-based semantic chunking.

Tuned for textbooks like NCERT that follow predictable structural patterns:
numbered sections, definition boxes, examples, activities, summaries, etc.

Uses PyMuPDF for extraction and spaCy for sentence segmentation.  Produces
*structural nodes* – chunks that carry their heading / section context so
downstream consumers know *where* in the book the content came from.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import fitz
import spacy

from Core.Embedder.constants import MAX_CHUNK_WORDS, MIN_CHUNK_CHARS, SPACY_MODEL

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
    node_hint: Optional[str] = None  # definition | example | process | concept | None

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
# PDF Extraction
# ──────────────────────────────────────────────────────────────────────

def extract_pdf(pdf_path: str) -> Tuple[str, List[bytes]]:
    """Extract plain text and raster images from a PDF.

    Returns ``(full_text, [image_bytes_png, ...])``.
    """
    doc = fitz.open(pdf_path)
    text_parts: List[str] = []
    images: List[bytes] = []

    for page in doc:
        text_parts.append(page.get_text("text"))

        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:  # CMYK → RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                images.append(pix.tobytes("png"))
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


def _detect_node_hint(line: str) -> Optional[str]:
    """Detect NCERT-specific markers to pre-classify the upcoming block."""
    if _RE_DEFINITION.match(line):
        return "definition"
    if _RE_EXAMPLE.match(line):
        return "example"
    if _RE_ACTIVITY.match(line):
        return "process"
    if _RE_SUMMARY.match(line) or _RE_QUESTION.match(line):
        return "concept"
    return None


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
    3. NCERT markers (Definition, Example, Activity …) set a ``node_hint``
       on the resulting chunk so the classifier can short-circuit.
    4. Within a section, sentences are grouped into chunks respecting
       ``MAX_CHUNK_WORDS`` using spaCy for proper sentence boundaries.
    5. Drops chunks shorter than ``MIN_CHUNK_CHARS``.
    """
    nlp = _get_nlp()
    lines = text.split("\n")
    nodes: List[StructuralNode] = []

    # Running state
    section_stack: List[str] = []
    current_heading: Optional[str] = None
    current_hint: Optional[str] = None
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
                    node_hint=current_hint,
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
                            node_hint=current_hint,
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
                        node_hint=current_hint,
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
            current_hint = _detect_node_hint(stripped)
            continue

        # Check for NCERT marker mid-section (e.g. "Definition:" inline)
        hint = _detect_node_hint(stripped)
        if hint and buffer:
            _flush()
            current_hint = hint

        buffer.append(stripped)

    # Final flush
    _flush()

    return nodes
