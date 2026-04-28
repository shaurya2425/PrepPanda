"""Mind-map generator — turn parsed chapter content into a hierarchical
concept graph suitable for interactive visualisation.

Two complementary strategies work together:

1. **Structure-aware parsing**
   Exploit the document's own structure (headings, bullet-lists,
   figure captions) that the NodeParser / VisualParser already expose.
   Headings become branch nodes, body text becomes leaf detail, and
   figures attach as visual annotations.

2. **Lightweight semantic extraction** (rule-based)
   Pattern-match common textbook constructs *without* a heavy model:
       • "X is defined as Y"       → ``definition``
       • "types of X"              → ``classification``
       • "process of X"            → ``steps``
       • "X differs from Y"       → ``comparison``
       • "for example / e.g."      → ``example``
       • bulleted / numbered lists → ``enumeration``

   Each match becomes a semantically-tagged leaf on the tree, making
   the mind-map far more useful than a heading-only outline.

Public API
----------
::

    from Core.Features.MindMap import MindMapBuilder

    # ── From raw PDF ────────────────────────────────────────────────
    tree = MindMapBuilder.from_pdf("lebo101.pdf")

    # ── From pre-parsed chunks (avoids re-parsing) ──────────────────
    from Core.Parser.NodeParser import parse_pdf_text
    chunks, refs = parse_pdf_text("lebo101.pdf")
    tree = MindMapBuilder.from_chunks(chunks, image_refs=refs)

    # ── Serialise ───────────────────────────────────────────────────
    tree.to_dict()   # nested dict ready for JSON / D3 / React-Flow
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Semantic tag taxonomy
# ─────────────────────────────────────────────────────────────────────

class SemanticTag(Enum):
    """Category assigned by the rule-based semantic extractor."""
    DEFINITION     = auto()   # "X is defined as Y"
    CLASSIFICATION = auto()   # "types of X", "kinds of X"
    STEPS          = auto()   # "process of X", "mechanism of X"
    COMPARISON     = auto()   # "X differs from Y", "distinguish between"
    EXAMPLE        = auto()   # "for example", "e.g.", "such as"
    ENUMERATION    = auto()   # bulleted / numbered lists
    KEY_TERM       = auto()   # bold / emphasised term
    FIGURE         = auto()   # figure caption node
    BODY           = auto()   # unclassified body text


# ─────────────────────────────────────────────────────────────────────
# Mind-map node
# ─────────────────────────────────────────────────────────────────────

@dataclass
class MindMapNode:
    """A single node in the mind-map tree.

    Attributes
    ----------
    id : str
        Unique identifier (UUID4 hex-slug for frontend keying).
    label : str
        Short display label (heading text, term, or summary phrase).
    detail : str
        Longer body text associated with this node (may be empty).
    tag : SemanticTag
        Semantic category from the rule extractor.
    depth : int
        Depth in the tree (0 = root).
    children : list[MindMapNode]
        Child nodes.
    figure_ids : list[str]
        Figure ref-IDs linked to this node (e.g. ``["1.1", "1.2"]``).
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    label: str = ""
    detail: str = ""
    tag: SemanticTag = SemanticTag.BODY
    depth: int = 0
    children: List[MindMapNode] = field(default_factory=list)
    figure_ids: List[str] = field(default_factory=list)

    # ── Serialisation ───────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Recursively convert to a plain dict (JSON-safe)."""
        d: Dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "tag": self.tag.name.lower(),
            "depth": self.depth,
        }
        if self.detail:
            d["detail"] = self.detail
        if self.figure_ids:
            d["figure_ids"] = self.figure_ids
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    def node_count(self) -> int:
        """Total nodes in this sub-tree (inclusive)."""
        return 1 + sum(c.node_count() for c in self.children)

    def leaf_count(self) -> int:
        """Number of leaf nodes (no children)."""
        if not self.children:
            return 1
        return sum(c.leaf_count() for c in self.children)


# ─────────────────────────────────────────────────────────────────────
# Semantic extraction rules (lightweight, no ML)
# ─────────────────────────────────────────────────────────────────────

# Each rule is a (compiled regex, SemanticTag, extractor) triple.
# The extractor receives the Match object and returns
# (label: str, detail: str).

_SEMANTIC_RULES: List[Tuple[re.Pattern, SemanticTag, Any]] = []


def _rule(pattern: str, tag: SemanticTag, flags: int = re.IGNORECASE):
    """Decorator that registers a semantic-extraction rule."""
    compiled = re.compile(pattern, flags)

    def _decorator(fn):
        _SEMANTIC_RULES.append((compiled, tag, fn))
        return fn

    return _decorator


# ─── RULE REGISTRATION ORDER MATTERS ───────────────────────────────
# More specific patterns (classification, steps, comparison, example)
# are registered FIRST so they claim spans before the broad definition
# pattern has a chance to match.

# ── 1. Classification / Taxonomy (high priority) ──────────────────
# "types of pollination", "kinds of seeds", "categories of …"

_RE_CLASSIFICATION = (
    r"(?:types?|kinds?|categories|forms?|varieties|classes)\s+of\s+"
    r"([A-Za-z\s\-']{3,60})"
)


@_rule(_RE_CLASSIFICATION, SemanticTag.CLASSIFICATION)
def _extract_classification(m: re.Match) -> Tuple[str, str]:
    topic = m.group(1).strip().rstrip(".")
    return f"Types of {topic}", ""


# ── 2. Process / Steps (high priority) ────────────────────────────
# "process of double fertilisation", "mechanism of …",
# "steps involved in …", "stages of …"

_RE_STEPS = (
    r"(?:process|mechanism|procedure|stages?|steps?(?:\s+involved)?)\s+"
    r"(?:of|in|for)\s+"
    r"([A-Za-z\s\-']{3,60})"
)


@_rule(_RE_STEPS, SemanticTag.STEPS)
def _extract_steps(m: re.Match) -> Tuple[str, str]:
    topic = m.group(1).strip().rstrip(".")
    return f"Process: {topic}", ""


# ── 3. Comparison (high priority) ─────────────────────────────────
# "X differs from Y", "difference between X and Y",
# "distinguish between", "compare X and Y"

_RE_COMPARISON = (
    r"(?:differ(?:s|ence)?|distinguish|compare|contrast)"
    r"(?:\s+between)?\s+"
    r"([A-Za-z\s\-']{3,40})"
    r"\s+(?:and|from|with)\s+"
    r"([A-Za-z\s\-']{3,40})"
)


@_rule(_RE_COMPARISON, SemanticTag.COMPARISON)
def _extract_comparison(m: re.Match) -> Tuple[str, str]:
    a = m.group(1).strip()
    b = m.group(2).strip().rstrip(".")
    return f"{a} vs {b}", ""


# ── 4. Examples (high priority) ───────────────────────────────────
# "for example, …", "e.g., …", "such as …"

_RE_EXAMPLE = (
    r"(?:for\s+example|e\.g\.|such\s+as|for\s+instance)"
    r"[,:]?\s+"
    r"(.{5,200}?)"
    r"(?:\.|;|$)"
)


@_rule(_RE_EXAMPLE, SemanticTag.EXAMPLE)
def _extract_example(m: re.Match) -> Tuple[str, str]:
    body = m.group(1).strip().rstrip(".")
    # Use first ~50 chars as label
    label = body[:50] + ("…" if len(body) > 50 else "")
    return f"Example: {label}", body


# ── 5. Definitions (lower priority — runs after specific rules) ───
# "Pollination is defined as the transfer of …"
# "Apomixis is a mode of …"

_RE_DEFINITION = (
    r"(?:^|\.\s+)"
    r"([A-Z][A-Za-z\s\-']{2,60}?)"            # term
    r"\s+(?:is|are|refers?\s+to|means?|may\s+be)\s+"
    r"(?:defined\s+as\s+|described\s+as\s+|called\s+|termed\s+|known\s+as\s+)?"
    r"(.{10,300}?)"                             # definition body
    r"(?:\.|$)"
)

# Words that signal other semantic categories — if the captured term
# starts with one of these the match belongs to a different rule.
_DEFINITION_REJECT_PREFIXES = re.compile(
    r"^(?:types?|kinds?|categories|forms?|varieties|classes|"
    r"process|mechanism|procedure|stages?|steps?|"
    r"there|these|those|it|they|we|he|she|the|this|that|"
    r"several|many|some|various|different|two|three|four|"
    r"for\s+example|e\.g\.|such\s+as)\b",
    re.IGNORECASE,
)


@_rule(_RE_DEFINITION, SemanticTag.DEFINITION)
def _extract_definition(m: re.Match) -> Tuple[str, str]:
    term = m.group(1).strip()
    # Reject if the "term" is actually a function-word phrase
    if _DEFINITION_REJECT_PREFIXES.match(term):
        raise ValueError("Not a definition")
    body = m.group(2).strip().rstrip(".")
    return term, f"{term}: {body}"


# ─────────────────────────────────────────────────────────────────────
# List detection (structure-aware)
# ─────────────────────────────────────────────────────────────────────

_RE_LIST_ITEM = re.compile(
    r"^\s*(?:[-•●▪▸▹◦➤➢★☆✦✧⁃]|\d+[.)]\s|[a-z][.)]\s|[ivxlc]+[.)]\s)",
    re.IGNORECASE,
)

_RE_NUMBERED_ITEM = re.compile(r"^\s*(\d+)[.)]\s+(.+)$")


def _detect_list_items(text: str) -> List[str]:
    """Return individual list items if *text* looks like a bulleted /
    numbered list, else empty list."""
    lines = text.strip().split("\n")
    items: List[str] = []
    for line in lines:
        stripped = line.strip()
        if _RE_LIST_ITEM.match(stripped):
            # Strip the bullet / number prefix
            clean = re.sub(
                r"^\s*(?:[-•●▪▸▹◦➤➢★☆✦✧⁃]|\d+[.)]\s*|[a-z][.)]\s*|[ivxlc]+[.)]\s*)",
                "",
                stripped,
                flags=re.IGNORECASE,
            ).strip()
            if clean:
                items.append(clean)
    return items


# ─────────────────────────────────────────────────────────────────────
# Figure caption parsing
# ─────────────────────────────────────────────────────────────────────

_RE_FIGURE_CAPTION = re.compile(
    r"^(?:figure|fig\.?)\s*(\d+(?:\.\d+)*)\s*[:\-\u2013\u2014.]?\s*(.*)",
    re.IGNORECASE,
)

_RE_FIG_REF_INLINE = re.compile(
    r"Fig(?:ure)?\.?\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────
# Heading depth heuristic
# ─────────────────────────────────────────────────────────────────────

_RE_NUMBERED_HEADING = re.compile(
    r"^(?:chapter\s+\d+|(?:\d+\.)+\d*)\s*[:\-\u2013\u2014]?\s*(.+)?$",
    re.IGNORECASE,
)


def _heading_depth(heading: str) -> int:
    """Estimate nesting depth from a heading string.

    "Chapter 1"      → 1
    "1.1 Pollination" → 2
    "1.1.2 Types"     → 3
    ALL-CAPS / title  → 2  (default sub-heading)
    """
    m = _RE_NUMBERED_HEADING.match(heading.strip())
    if m:
        # Count dots in the numeric prefix
        prefix = heading.strip().split()[0]
        dots = prefix.count(".")
        # "1.1" → depth 2, "1.1.2" → depth 3
        if prefix.lower().startswith("chapter"):
            return 1
        return max(1, dots + 1)
    return 2  # generic sub-heading


# ─────────────────────────────────────────────────────────────────────
# Core: run all semantic rules on a chunk
# ─────────────────────────────────────────────────────────────────────

@dataclass
class _SemanticHit:
    """One matched semantic pattern within a chunk."""
    label: str
    detail: str
    tag: SemanticTag
    span_start: int   # character offset in source text


def _run_semantic_rules(text: str) -> List[_SemanticHit]:
    """Apply every registered rule; return de-duplicated hits sorted
    by position in the source text."""
    hits: List[_SemanticHit] = []
    seen_spans: set = set()

    for regex, tag, extractor in _SEMANTIC_RULES:
        for m in regex.finditer(text):
            # Avoid overlapping extractions
            key = (m.start(), m.end())
            if key in seen_spans:
                continue
            # Check for substantial overlap with existing hits
            overlaps = False
            for s in seen_spans:
                if not (key[1] <= s[0] or key[0] >= s[1]):
                    overlaps = True
                    break
            if overlaps:
                continue

            seen_spans.add(key)
            try:
                label, detail = extractor(m)
                hits.append(_SemanticHit(
                    label=label,
                    detail=detail,
                    tag=tag,
                    span_start=m.start(),
                ))
            except Exception:
                logger.debug("Extraction failed for rule %s", tag)

    hits.sort(key=lambda h: h.span_start)
    return hits


# ─────────────────────────────────────────────────────────────────────
# Builder
# ─────────────────────────────────────────────────────────────────────

class MindMapBuilder:
    """Construct a ``MindMapNode`` tree from parsed chapter data.

    Two entry points:

    ``from_pdf(path)``
        Parse the PDF first, then build the tree.

    ``from_chunks(chunks, image_refs)``
        Build directly from pre-parsed ``TextChunk`` objects
        (avoids re-parsing when the pipeline has already run).
    """

    # ── From PDF ────────────────────────────────────────────────────

    @staticmethod
    def from_pdf(
        pdf_path: str,
        *,
        chapter_title: Optional[str] = None,
    ) -> MindMapNode:
        """Parse *pdf_path* with ``NodeParser`` and build the mind-map.

        Parameters
        ----------
        pdf_path : str
            Path to the chapter PDF.
        chapter_title : str, optional
            Override root label. Defaults to filename stem.
        """
        from Core.Parser.NodeParser import parse_pdf_text

        chunks, image_refs = parse_pdf_text(pdf_path)

        if not chapter_title:
            import os
            chapter_title = os.path.splitext(os.path.basename(pdf_path))[0]

        return MindMapBuilder.from_chunks(
            chunks,
            image_refs=image_refs,
            root_label=chapter_title,
        )

    # ── From pre-parsed chunks ──────────────────────────────────────

    @staticmethod
    def from_chunks(
        chunks,
        *,
        image_refs=None,
        root_label: str = "Chapter",
    ) -> MindMapNode:
        """Build a mind-map tree from ``TextChunk`` objects.

        Parameters
        ----------
        chunks : list[TextChunk]
            From ``NodeParser.parse_pdf_text``.
        image_refs : list[ImageRef], optional
            Deduplicated figure references (used for annotation).
        root_label : str
            Label for the root node.

        Returns
        -------
        MindMapNode
            Root of the mind-map tree.
        """
        root = MindMapNode(
            label=root_label,
            tag=SemanticTag.BODY,
            depth=0,
        )

        # Build a lookup: figure_ref_id → ImageRef for enrichment
        ref_lookup: Dict[str, Any] = {}
        if image_refs:
            for ref in image_refs:
                ref_lookup[ref.ref_id] = ref

        # ── Walk chunks in order, reconstruct heading hierarchy ─────
        # We maintain a stack of (depth, node) to track where to
        # attach new nodes.
        stack: List[Tuple[int, MindMapNode]] = [(0, root)]

        for chunk in chunks:
            section = chunk.section_title or ""
            content = chunk.content or ""

            # ── Heading node (from section_title changes) ───────────
            if section:
                depth = _heading_depth(section)
                heading_node = _find_or_create_heading(
                    stack, section, depth,
                )
                # Process the chunk content under this heading
                _attach_content(
                    parent=heading_node,
                    content=content,
                    depth=depth + 1,
                    figure_refs=chunk.figure_refs,
                    ref_lookup=ref_lookup,
                )
            else:
                # No section — attach to current deepest branch
                parent = stack[-1][1]
                parent_depth = stack[-1][0]
                _attach_content(
                    parent=parent,
                    content=content,
                    depth=parent_depth + 1,
                    figure_refs=chunk.figure_refs,
                    ref_lookup=ref_lookup,
                )

        # ── Attach standalone figure nodes that weren't covered ─────
        _attach_orphan_figures(root, ref_lookup)

        logger.info(
            "MindMap built: %d nodes, %d leaves",
            root.node_count(),
            root.leaf_count(),
        )
        return root

    # ── From DB chunks (raw dicts from PostgresHandler) ─────────────

    @staticmethod
    def from_db_chunks(
        chunk_dicts: List[Dict[str, Any]],
        *,
        root_label: str = "Chapter",
    ) -> MindMapNode:
        """Build a mind-map from raw DB chunk dicts.

        Useful when chunks are already stored and you don't want to
        re-parse the PDF.  Each dict must have ``content`` and
        optionally ``section_title``.

        Parameters
        ----------
        chunk_dicts : list[dict]
            Rows from ``core.chunks`` (as returned by
            ``PostgresHandler.get_chunks_by_ids``).
        root_label : str
            Label for the root node.
        """
        root = MindMapNode(
            label=root_label,
            tag=SemanticTag.BODY,
            depth=0,
        )
        stack: List[Tuple[int, MindMapNode]] = [(0, root)]

        for row in sorted(chunk_dicts, key=lambda r: r.get("position_index", 0)):
            section = row.get("section_title") or ""
            content = row.get("content", "")

            if section:
                depth = _heading_depth(section)
                heading_node = _find_or_create_heading(stack, section, depth)
                _attach_content(
                    parent=heading_node,
                    content=content,
                    depth=depth + 1,
                    figure_refs=[],
                    ref_lookup={},
                )
            else:
                parent = stack[-1][1]
                parent_depth = stack[-1][0]
                _attach_content(
                    parent=parent,
                    content=content,
                    depth=parent_depth + 1,
                    figure_refs=[],
                    ref_lookup={},
                )

        logger.info(
            "MindMap (DB) built: %d nodes, %d leaves",
            root.node_count(),
            root.leaf_count(),
        )
        return root


# ─────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────

def _find_or_create_heading(
    stack: List[Tuple[int, MindMapNode]],
    heading: str,
    depth: int,
) -> MindMapNode:
    """Find an existing heading node at *depth* or create one.

    Maintains the stack so that subsequent content attaches under
    the correct heading.
    """
    # Pop stack back to the appropriate parent depth
    while len(stack) > 1 and stack[-1][0] >= depth:
        stack.pop()

    parent = stack[-1][1]

    # Check if this heading already exists as a child
    for child in parent.children:
        if child.label == heading.strip():
            # Re-push so further content goes under this heading
            stack.append((depth, child))
            return child

    # Create new heading node
    node = MindMapNode(
        label=heading.strip(),
        tag=SemanticTag.BODY,
        depth=depth,
    )
    parent.children.append(node)
    stack.append((depth, node))
    return node


def _attach_content(
    parent: MindMapNode,
    content: str,
    depth: int,
    figure_refs: List[str],
    ref_lookup: Dict[str, Any],
) -> None:
    """Parse *content* and attach semantic sub-nodes to *parent*.

    Steps:
    1. Detect bulleted/numbered lists → ``ENUMERATION`` children.
    2. Run semantic rules → ``DEFINITION``, ``CLASSIFICATION``, etc.
    3. Detect inline figure references → ``FIGURE`` annotations.
    4. Remaining text → a single ``BODY`` leaf (if substantial).
    """
    if not content or not content.strip():
        return

    content = content.strip()
    added_something = False

    # ── 1. List detection ───────────────────────────────────────────
    list_items = _detect_list_items(content)
    if len(list_items) >= 2:
        # Create an enumeration parent node
        # Try to find a preamble line before the list
        lines = content.split("\n")
        preamble = ""
        for line in lines:
            if not _RE_LIST_ITEM.match(line.strip()):
                preamble = line.strip()
                break

        enum_label = preamble if preamble else f"{len(list_items)} items"
        enum_node = MindMapNode(
            label=enum_label,
            tag=SemanticTag.ENUMERATION,
            depth=depth,
        )

        for item in list_items:
            item_node = MindMapNode(
                label=_truncate(item, 80),
                detail=item if len(item) > 80 else "",
                tag=SemanticTag.ENUMERATION,
                depth=depth + 1,
            )
            # Run semantic rules on each list item for richer tagging
            hits = _run_semantic_rules(item)
            if hits:
                item_node.tag = hits[0].tag
                if hits[0].detail:
                    item_node.detail = hits[0].detail
            enum_node.children.append(item_node)

        parent.children.append(enum_node)
        added_something = True

    # ── 2. Semantic rule extraction ─────────────────────────────────
    hits = _run_semantic_rules(content)
    for hit in hits:
        node = MindMapNode(
            label=hit.label,
            detail=hit.detail,
            tag=hit.tag,
            depth=depth,
        )
        parent.children.append(node)
        added_something = True

    # ── 3. Figure references ────────────────────────────────────────
    fig_ids_in_text: List[str] = []
    for m in _RE_FIG_REF_INLINE.finditer(content):
        fig_id = m.group(1)
        if fig_id not in fig_ids_in_text:
            fig_ids_in_text.append(fig_id)

    # Also use pre-extracted figure_refs from the chunk
    for ref_id in figure_refs:
        if ref_id not in fig_ids_in_text:
            fig_ids_in_text.append(ref_id)

    for fig_id in fig_ids_in_text:
        ref = ref_lookup.get(fig_id)
        fig_label = f"Figure {fig_id}"
        if ref and hasattr(ref, "title") and ref.title:
            fig_label += f": {ref.title}"

        fig_node = MindMapNode(
            label=fig_label,
            tag=SemanticTag.FIGURE,
            depth=depth,
            figure_ids=[fig_id],
        )
        parent.children.append(fig_node)
        added_something = True

        # Propagate figure_id up to parent
        if fig_id not in parent.figure_ids:
            parent.figure_ids.append(fig_id)

    # ── 4. Fallback BODY leaf ───────────────────────────────────────
    # Only add if we didn't extract anything meaningful and the
    # content is long enough to be informative.
    if not added_something and len(content) >= 40:
        body_node = MindMapNode(
            label=_truncate(content, 80),
            detail=content if len(content) > 80 else "",
            tag=SemanticTag.BODY,
            depth=depth,
        )
        parent.children.append(body_node)


def _attach_orphan_figures(
    root: MindMapNode,
    ref_lookup: Dict[str, Any],
) -> None:
    """Attach figure refs that weren't covered by any chunk."""
    # Collect all figure IDs already in the tree
    covered: set = set()
    _collect_figure_ids(root, covered)

    orphans = [
        ref for ref_id, ref in ref_lookup.items()
        if ref_id not in covered
    ]

    if not orphans:
        return

    # Create a "Figures" section for orphans
    fig_section = MindMapNode(
        label="Figures",
        tag=SemanticTag.FIGURE,
        depth=1,
    )
    for ref in orphans:
        label = f"Figure {ref.ref_id}"
        if hasattr(ref, "title") and ref.title:
            label += f": {ref.title}"
        fig_section.children.append(MindMapNode(
            label=label,
            tag=SemanticTag.FIGURE,
            depth=2,
            figure_ids=[ref.ref_id],
        ))

    root.children.append(fig_section)


def _collect_figure_ids(node: MindMapNode, acc: set) -> None:
    """Recursively collect all figure IDs in the tree."""
    for fid in node.figure_ids:
        acc.add(fid)
    for child in node.children:
        _collect_figure_ids(child, acc)


def _truncate(text: str, max_len: int = 80) -> str:
    """Truncate text to *max_len* characters with an ellipsis."""
    # Clean up whitespace
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    # Cut at last word boundary before max_len
    cut = text[:max_len].rsplit(" ", 1)[0]
    return cut + "…"
