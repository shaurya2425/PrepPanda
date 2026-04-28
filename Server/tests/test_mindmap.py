"""Unit tests for Core.Features.MindMap — validates structure-aware parsing
and semantic extraction rules without needing a PDF or database.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Core.Features.MindMap import (
    MindMapBuilder,
    MindMapNode,
    SemanticTag,
    _run_semantic_rules,
    _detect_list_items,
    _heading_depth,
    _truncate,
)


# ─────────────────────────────────────────────────────────────────────
# Semantic rule tests
# ─────────────────────────────────────────────────────────────────────

def test_definition_extraction():
    text = "Pollination is defined as the transfer of pollen grains from the anther to the stigma of a pistil."
    hits = _run_semantic_rules(text)
    assert any(h.tag == SemanticTag.DEFINITION for h in hits), f"Expected DEFINITION, got {[h.tag for h in hits]}"
    defn = next(h for h in hits if h.tag == SemanticTag.DEFINITION)
    assert "Pollination" in defn.label
    print(f"  ✓ Definition: {defn.label}")


def test_definition_is_are():
    text = "Apomixis is a mode of asexual reproduction that mimics sexual reproduction."
    hits = _run_semantic_rules(text)
    assert any(h.tag == SemanticTag.DEFINITION for h in hits), f"Expected DEFINITION, got {[h.tag for h in hits]}"
    print(f"  ✓ Definition (is): {hits[0].label}")


def test_classification_extraction():
    text = "There are several types of pollination in flowering plants."
    hits = _run_semantic_rules(text)
    assert any(h.tag == SemanticTag.CLASSIFICATION for h in hits), f"Expected CLASSIFICATION, got {[h.tag for h in hits]}"
    cls = next(h for h in hits if h.tag == SemanticTag.CLASSIFICATION)
    assert "pollination" in cls.label.lower()
    print(f"  ✓ Classification: {cls.label}")


def test_steps_extraction():
    text = "The process of double fertilisation involves two fusions."
    hits = _run_semantic_rules(text)
    assert any(h.tag == SemanticTag.STEPS for h in hits), f"Expected STEPS, got {[h.tag for h in hits]}"
    stp = next(h for h in hits if h.tag == SemanticTag.STEPS)
    assert "double fertilisation" in stp.label.lower()
    print(f"  ✓ Steps: {stp.label}")


def test_comparison_extraction():
    text = "We can distinguish between self-pollination and cross-pollination."
    hits = _run_semantic_rules(text)
    assert any(h.tag == SemanticTag.COMPARISON for h in hits), f"Expected COMPARISON, got {[h.tag for h in hits]}"
    cmp = next(h for h in hits if h.tag == SemanticTag.COMPARISON)
    assert "vs" in cmp.label
    print(f"  ✓ Comparison: {cmp.label}")


def test_example_extraction():
    text = "Some plants show cleistogamy, for example, Viola and Oxalis."
    hits = _run_semantic_rules(text)
    assert any(h.tag == SemanticTag.EXAMPLE for h in hits), f"Expected EXAMPLE, got {[h.tag for h in hits]}"
    ex = next(h for h in hits if h.tag == SemanticTag.EXAMPLE)
    print(f"  ✓ Example: {ex.label}")


# ─────────────────────────────────────────────────────────────────────
# List detection tests
# ─────────────────────────────────────────────────────────────────────

def test_list_detection_bullets():
    text = "Features of wind-pollinated flowers:\n• Light and non-sticky pollen\n• Well-exposed stamens\n• Large feathery stigma"
    items = _detect_list_items(text)
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    print(f"  ✓ Bullet list: {len(items)} items")


def test_list_detection_numbered():
    text = "Steps:\n1) Pollen lands on stigma\n2) Pollen tube grows\n3) Fertilisation occurs"
    items = _detect_list_items(text)
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    print(f"  ✓ Numbered list: {len(items)} items")


def test_list_detection_dash():
    text = "Components:\n- Sepals\n- Petals\n- Stamens\n- Carpels"
    items = _detect_list_items(text)
    assert len(items) == 4, f"Expected 4 items, got {len(items)}"
    print(f"  ✓ Dash list: {len(items)} items")


# ─────────────────────────────────────────────────────────────────────
# Heading depth tests
# ─────────────────────────────────────────────────────────────────────

def test_heading_depth():
    assert _heading_depth("Chapter 1 – Reproduction") == 1
    assert _heading_depth("1.1 Pollination") == 2
    assert _heading_depth("1.2.3 Wind pollination") == 3
    assert _heading_depth("SUMMARY") == 2
    print("  ✓ Heading depth heuristic")


# ─────────────────────────────────────────────────────────────────────
# Tree building from mock chunks
# ─────────────────────────────────────────────────────────────────────

def test_tree_from_mock_chunks():
    """Build a tree from fake TextChunk-like objects."""
    from dataclasses import dataclass, field as dc_field
    from typing import List, Optional

    @dataclass
    class FakeChunk:
        content: str
        section_title: Optional[str] = None
        section_path: List[str] = dc_field(default_factory=list)
        figure_refs: List[str] = dc_field(default_factory=list)

    chunks = [
        FakeChunk(
            content="Sexual reproduction involves the fusion of male and female gametes.",
            section_title="Chapter 1 – Reproduction",
        ),
        FakeChunk(
            content="Pollination is defined as the transfer of pollen grains from the anther to the stigma.",
            section_title="1.1 Pollination",
            figure_refs=["1.1"],
        ),
        FakeChunk(
            content="There are two types of pollination:\n- Self-pollination\n- Cross-pollination",
            section_title="1.1 Pollination",
        ),
        FakeChunk(
            content="The process of double fertilisation involves two fusions that occur inside the embryo sac.",
            section_title="1.2 Fertilisation",
            figure_refs=["1.3"],
        ),
        FakeChunk(
            content="Some plants reproduce by apomixis, for example, citrus and mango.",
            section_title="1.3 Apomixis",
        ),
    ]

    @dataclass
    class FakeRef:
        ref_id: str
        title: str
        display: str

    refs = [
        FakeRef("1.1", "Stamen and Pistil", "Fig 1.1 Stamen and Pistil"),
        FakeRef("1.3", "Double Fertilisation", "Fig 1.3 Double Fertilisation"),
    ]

    tree = MindMapBuilder.from_chunks(chunks, image_refs=refs, root_label="Sexual Reproduction in Flowering Plants")

    assert tree.label == "Sexual Reproduction in Flowering Plants"
    assert tree.depth == 0
    assert len(tree.children) > 0

    tree_dict = tree.to_dict()
    assert "children" in tree_dict
    assert tree_dict["label"] == "Sexual Reproduction in Flowering Plants"

    print(f"  ✓ Tree built: {tree.node_count()} nodes, {tree.leaf_count()} leaves")

    # Verify semantic tags are present
    all_tags = _collect_tags(tree)
    assert SemanticTag.DEFINITION in all_tags, "Expected a DEFINITION node"
    assert SemanticTag.ENUMERATION in all_tags, "Expected an ENUMERATION node"
    assert SemanticTag.FIGURE in all_tags, "Expected a FIGURE node"
    print(f"  ✓ Tags found: {[t.name for t in all_tags]}")

    # Pretty-print the tree
    print("\n  ── Generated Mind-Map Tree ──")
    _print_tree(tree, indent=2)


def test_tree_from_db_chunks():
    """Build from raw DB dicts."""
    rows = [
        {"content": "Photosynthesis is the process by which green plants make food.", "section_title": "1.1 Photosynthesis", "position_index": 0},
        {"content": "Types of photosynthesis:\n• C3 pathway\n• C4 pathway\n• CAM pathway", "section_title": "1.1 Photosynthesis", "position_index": 1},
        {"content": "The mechanism of C4 fixation involves spatial separation of carbon fixation.", "section_title": "1.2 C4 Pathway", "position_index": 2},
    ]
    tree = MindMapBuilder.from_db_chunks(rows, root_label="Photosynthesis")
    assert tree.node_count() > 3
    print(f"  ✓ DB tree built: {tree.node_count()} nodes")
    _print_tree(tree, indent=2)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _collect_tags(node: MindMapNode) -> set:
    tags = {node.tag}
    for child in node.children:
        tags |= _collect_tags(child)
    return tags


def _print_tree(node: MindMapNode, indent: int = 0) -> None:
    prefix = "  " * indent
    tag = node.tag.name[:4]
    figs = f" 📊{node.figure_ids}" if node.figure_ids else ""
    print(f"{prefix}{'├─' if indent else '●'} [{tag}] {node.label}{figs}")
    for child in node.children:
        _print_tree(child, indent + 1)


# ─────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("═══ Semantic Extraction Rules ═══")
    test_definition_extraction()
    test_definition_is_are()
    test_classification_extraction()
    test_steps_extraction()
    test_comparison_extraction()
    test_example_extraction()

    print("\n═══ List Detection ═══")
    test_list_detection_bullets()
    test_list_detection_numbered()
    test_list_detection_dash()

    print("\n═══ Heading Depth ═══")
    test_heading_depth()

    print("\n═══ Tree Building (Mock Chunks) ═══")
    test_tree_from_mock_chunks()

    print("\n═══ Tree Building (DB Chunks) ═══")
    test_tree_from_db_chunks()

    print("\n\n✅ All MindMap tests passed!")
