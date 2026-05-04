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
import os
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from groq import Groq

from Routers.deps import PgDep
from Core.cache import cache_store

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
    cache_key = cache_store.make_key("mindmap_tree", str(chapter_id))
    cached = cache_store.get("mindmaps", cache_key)
    if cached is not None:
        logger.info("Cache HIT  mindmap tree %s", chapter_id)
        return MindMapOut(**cached)

    chapter_row, chunk_rows = await _fetch_chapter_data(pg, chapter_id)
    chapter_title = chapter_row["title"]

    tree = await _get_or_generate_concept_graph(chapter_id, chapter_row, chunk_rows, pg)

    result = MindMapOut(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        node_count=_count_nodes(tree),
        leaf_count=_count_leaves(tree),
        tree=tree,
    )
    await cache_store.put("mindmaps", cache_key, result.model_dump(mode="json"))
    return result


@router.get(
    "/{chapter_id}/flat",
    response_model=MindMapFlatOut,
    summary="Get a flat node list (with parent IDs) for a chapter",
)
async def get_mindmap_flat(
    chapter_id: uuid.UUID,
    pg: PgDep,
) -> MindMapFlatOut:
    cache_key = cache_store.make_key("mindmap_flat", str(chapter_id))
    cached = cache_store.get("mindmaps", cache_key)
    if cached is not None:
        logger.info("Cache HIT  mindmap flat %s", chapter_id)
        return MindMapFlatOut(**cached)

    chapter_row, chunk_rows = await _fetch_chapter_data(pg, chapter_id)
    chapter_title = chapter_row["title"]

    tree = await _get_or_generate_concept_graph(chapter_id, chapter_row, chunk_rows, pg)

    flat: List[FlatNode] = []
    _flatten(tree, parent_id=None, acc=flat)

    result = MindMapFlatOut(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        nodes=flat,
    )
    await cache_store.put("mindmaps", cache_key, result.model_dump(mode="json"))
    return result


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

    chapter_title = chapter_row["title"]

    tree = await _get_or_generate_concept_graph(chapter_id, dict(chapter_row), chunk_rows, pg, is_range=True)

    return MindMapOut(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        node_count=_count_nodes(tree),
        leaf_count=_count_leaves(tree),
        tree=tree,
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

    chapter_title = chapter_row["title"]

    tree = await _get_or_generate_concept_graph(chapter_id, dict(chapter_row), chunk_rows, pg, is_range=True)

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


async def _get_or_generate_concept_graph(
    chapter_id: uuid.UUID,
    chapter_row: dict,
    chunk_rows: list,
    pg: PgDep,
    is_range: bool = False
) -> dict:
    if not is_range and chapter_row.get("concept_graph"):
        if isinstance(chapter_row["concept_graph"], str):
            return json.loads(chapter_row["concept_graph"])
        return chapter_row["concept_graph"]

    context = "\n".join([c["content"] for c in chunk_rows])
    prompt = f"""You are an expert educational structuralist. 
Read the following textbook material and construct a comprehensive, hierarchical concept graph (mind map).
Return ONLY a valid JSON object representing the root node, matching this exact schema recursively:
{{
  "id": "unique_string_id",
  "label": "Short Topic Name",
  "tag": "definition",
  "depth": 0,
  "detail": "A brief 1-2 sentence explanation",
  "figure_ids": [],
  "children": [ /* array of child nodes matching this same schema */ ]
}}
Tags must be one of: core_concept, definition, classification, steps, comparison, example, enumeration, body.
The root node must have depth 0, its children depth 1, and so on. Make it highly structured.

Material:
{context[:20000]}
"""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set.")

    client = Groq(api_key=key)
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    raw = completion.choices[0].message.content
    try:
        tree = json.loads(raw)
    except Exception as e:
        logger.error(f"Failed to parse Groq concept graph JSON: {e}\nRaw: {raw}")
        raise HTTPException(status_code=500, detail="Failed to parse concept graph JSON from LLM.")

    if not is_range:
        await pg.update_chapter_concept_graph(chapter_id, tree)

    return tree


def _flatten(
    node: dict,
    parent_id: Optional[str],
    acc: List[FlatNode],
) -> None:
    acc.append(FlatNode(
        id=str(node.get("id", str(uuid.uuid4()))),
        parent_id=parent_id,
        label=node.get("label", "Unknown"),
        tag=node.get("tag", "body").lower(),
        depth=node.get("depth", 0),
        detail=node.get("detail") or None,
        figure_ids=node.get("figure_ids", []),
    ))
    node_id = str(node.get("id"))
    for child in node.get("children", []):
        _flatten(child, parent_id=node_id, acc=acc)


def _count_nodes(node: dict) -> int:
    return 1 + sum(_count_nodes(c) for c in node.get("children", []))


def _count_leaves(node: dict) -> int:
    children = node.get("children", [])
    if not children:
        return 1
    return sum(_count_leaves(c) for c in children)

