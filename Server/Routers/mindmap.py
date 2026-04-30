"""MindMap router — generate a hierarchical concept map for a chapter.

Endpoints
---------
GET /mindmap/{chapter_id}
    Build and return a mind-map tree for the stored chunks of a chapter.

GET /mindmap/{chapter_id}/flat
    Same data but flattened into a node list with parent IDs, easier
    for some frontend graph libraries (e.g. React-Flow).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from Core.Features.MindMap import MindMapBuilder, MindMapNode, SemanticTag
from Routers.deps import PgDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mindmap", tags=["mindmap"])


# ─────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────

class MindMapOut(BaseModel):
    """Nested mind-map tree as a plain dict — JSON-ready for D3 / React."""
    chapter_id: uuid.UUID
    chapter_title: str
    node_count: int
    leaf_count: int
    tree: Dict[str, Any]


class FlatNode(BaseModel):
    id: str
    parent_id: Optional[str] = None
    label: str
    tag: str
    depth: int
    detail: Optional[str] = None
    figure_ids: List[str] = []


class MindMapFlatOut(BaseModel):
    chapter_id: uuid.UUID
    chapter_title: str
    nodes: List[FlatNode]


# ─────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────

@router.get(
    "/{chapter_id}",
    response_model=MindMapOut,
    summary="Get a nested mind-map tree for a chapter",
)
async def get_mindmap(
    chapter_id: uuid.UUID,
    pg: PgDep,
) -> MindMapOut:
    """
    Build a hierarchical mind-map from all chunks stored for the given
    chapter.

    The tree is returned as a nested JSON object with the following node
    fields:
    - ``id``         — unique node identifier
    - ``label``      — display text
    - ``tag``        — semantic category: ``definition``, ``classification``,
                       ``steps``, ``comparison``, ``example``,
                       ``enumeration``, ``figure``, or ``body``
    - ``depth``      — nesting level (0 = root)
    - ``detail``     — longer body text (optional)
    - ``figure_ids`` — list of linked figure IDs (optional)
    - ``children``   — nested child nodes
    """
    chapter_row, chunk_rows = await _fetch_chapter_data(pg, chapter_id)

    chapter_title = chapter_row["title"]
    chunk_dicts = [pg._record_to_dict(r) for r in chunk_rows]

    tree: MindMapNode = MindMapBuilder.from_db_chunks(
        chunk_dicts,
        root_label=chapter_title,
    )

    return MindMapOut(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        node_count=tree.node_count(),
        leaf_count=tree.leaf_count(),
        tree=tree.to_dict(),
    )


@router.get(
    "/{chapter_id}/flat",
    response_model=MindMapFlatOut,
    summary="Get a flat node list (with parent IDs) for a chapter",
)
async def get_mindmap_flat(
    chapter_id: uuid.UUID,
    pg: PgDep,
) -> MindMapFlatOut:
    """
    Same mind-map data as the nested endpoint, but serialised as a
    **flat list of nodes** each carrying a ``parent_id``.

    This format is directly usable by React-Flow and similar libraries
    that expect a flat edge list rather than a recursive tree.
    """
    chapter_row, chunk_rows = await _fetch_chapter_data(pg, chapter_id)

    chapter_title = chapter_row["title"]
    chunk_dicts = [pg._record_to_dict(r) for r in chunk_rows]

    tree: MindMapNode = MindMapBuilder.from_db_chunks(
        chunk_dicts,
        root_label=chapter_title,
    )

    flat: List[FlatNode] = []
    _flatten(tree, parent_id=None, acc=flat)

    return MindMapFlatOut(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        nodes=flat,
    )


# ── Chunk-range mindmap ──────────────────────────────────────────────

class ChunkRangeIn(BaseModel):
    """Define a chunk position range for a partial mind-map."""
    start: int = Field(..., ge=0, description="Start position_index (inclusive)")
    end:   int = Field(..., ge=0, description="End position_index (inclusive)")


class ChunkBoundsOut(BaseModel):
    chapter_id: uuid.UUID
    min_pos: int
    max_pos: int
    total: int


@router.get(
    "/{chapter_id}/bounds",
    response_model=ChunkBoundsOut,
    summary="Get chunk position bounds for a chapter",
)
async def get_chunk_bounds(
    chapter_id: uuid.UUID,
    pg: PgDep,
) -> ChunkBoundsOut:
    """
    Return the min / max ``position_index`` and total chunk count for a
    chapter.  Useful for the frontend to know valid ranges before
    requesting a partial mind-map.
    """
    bounds = await pg.get_chapter_chunk_bounds(chapter_id)
    if not bounds:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found for chapter {chapter_id}.",
        )
    return ChunkBoundsOut(chapter_id=chapter_id, **bounds)


@router.post(
    "/{chapter_id}/range",
    response_model=MindMapOut,
    summary="Build a mind-map from a chunk range",
)
async def get_mindmap_range(
    chapter_id: uuid.UUID,
    body: ChunkRangeIn,
    pg: PgDep,
) -> MindMapOut:
    """
    Build a mind-map from a **subset** of chunks defined by
    ``position_index`` range ``[start, end]``.

    This lets the frontend request a focused mind-map for a specific
    section of a chapter instead of the entire chapter.
    """
    pool = pg._pool_guard()
    chapter_row = await pool.fetchrow(
        "SELECT * FROM core.chapters WHERE chapter_id = $1", chapter_id
    )
    if not chapter_row:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found.")

    if body.start > body.end:
        raise HTTPException(status_code=422, detail="start must be ≤ end")

    chunk_rows = await pg.get_chunks_in_range(chapter_id, body.start, body.end)
    if not chunk_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found in range [{body.start}, {body.end}] for chapter {chapter_id}.",
        )

    chunk_dicts = [pg._record_to_dict(r) if hasattr(r, 'keys') else r for r in chunk_rows]
    chapter_title = chapter_row["title"]

    tree: MindMapNode = MindMapBuilder.from_db_chunks(
        chunk_dicts,
        root_label=f"{chapter_title} (chunks {body.start}–{body.end})",
    )

    return MindMapOut(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        node_count=tree.node_count(),
        leaf_count=tree.leaf_count(),
        tree=tree.to_dict(),
    )


@router.post(
    "/{chapter_id}/range/flat",
    response_model=MindMapFlatOut,
    summary="Flat mind-map from a chunk range",
)
async def get_mindmap_range_flat(
    chapter_id: uuid.UUID,
    body: ChunkRangeIn,
    pg: PgDep,
) -> MindMapFlatOut:
    """
    Same as ``/range`` but returns a flat node list instead of a
    nested tree.
    """
    pool = pg._pool_guard()
    chapter_row = await pool.fetchrow(
        "SELECT * FROM core.chapters WHERE chapter_id = $1", chapter_id
    )
    if not chapter_row:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found.")

    if body.start > body.end:
        raise HTTPException(status_code=422, detail="start must be ≤ end")

    chunk_rows = await pg.get_chunks_in_range(chapter_id, body.start, body.end)
    if not chunk_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found in range [{body.start}, {body.end}] for chapter {chapter_id}.",
        )

    chunk_dicts = [pg._record_to_dict(r) if hasattr(r, 'keys') else r for r in chunk_rows]
    chapter_title = chapter_row["title"]

    tree: MindMapNode = MindMapBuilder.from_db_chunks(
        chunk_dicts,
        root_label=f"{chapter_title} (chunks {body.start}–{body.end})",
    )

    flat: List[FlatNode] = []
    _flatten(tree, parent_id=None, acc=flat)

    return MindMapFlatOut(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        nodes=flat,
    )


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

async def _fetch_chapter_data(pg: PgDep, chapter_id: uuid.UUID):
    """Return (chapter_row, chunk_rows) or raise 404."""
    pool = pg._pool_guard()
    chapter_row = await pool.fetchrow(
        "SELECT * FROM core.chapters WHERE chapter_id = $1", chapter_id
    )
    if not chapter_row:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found.")

    chunk_rows = await pool.fetch(
        "SELECT * FROM core.chunks WHERE chapter_id = $1 ORDER BY position_index",
        chapter_id,
    )
    if not chunk_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found for chapter {chapter_id}. Has it been ingested?",
        )

    return chapter_row, chunk_rows


def _flatten(
    node: MindMapNode,
    parent_id: Optional[str],
    acc: List[FlatNode],
) -> None:
    """Recursively flatten the tree into acc."""
    acc.append(FlatNode(
        id=node.id,
        parent_id=parent_id,
        label=node.label,
        tag=node.tag.name.lower(),
        depth=node.depth,
        detail=node.detail or None,
        figure_ids=node.figure_ids,
    ))
    for child in node.children:
        _flatten(child, parent_id=node.id, acc=acc)
