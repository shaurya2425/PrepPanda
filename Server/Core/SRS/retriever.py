"""Retriever — query normalisation, embedding, and chunk retrieval.

Steps handled:
1. Normalise the incoming user query
2. Embed it with ChunkEmbedder
3. Retrieve relevant chunks (hybrid: semantic + keyword)
4. Expand with neighbour chunks for context continuity

Usage
-----
::

    from Core.SRS.retriever import Retriever

    retriever = Retriever(pg=pg, embedder=embedder)
    result    = await retriever.retrieve(
        query="What is double fertilisation?",
        chapter_id=chapter_id,
    )
    # result.chunks       → ordered list of chunk dicts
    # result.images       → list of image dicts linked to those chunks
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from Core.Parser.embedder import ChunkEmbedder
from Core.Storage.PostgresHandler import PostgresHandler

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────

DEFAULT_SEMANTIC_K = 6       # top-k semantic results
DEFAULT_KEYWORD_K = 4        # top-k keyword (BM25) results
NEIGHBOUR_WINDOW = 1         # ±N chunks around each hit


# ─────────────────────────────────────────────────────────────────────
# Result
# ─────────────────────────────────────────────────────────────────────

@dataclass
class RetrievalResult:
    """Everything the context builder needs."""
    query_normalised: str
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Query normalisation
# ─────────────────────────────────────────────────────────────────────

_STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "of", "in", "and", "or",
    "how", "does", "do", "can", "which", "where", "when", "why",
    "explain", "describe", "define", "discuss", "name", "list",
    "give", "write", "mention", "state", "differentiate",
}

def normalise_query(query: str) -> str:
    """Clean and lightly normalise a user query.

    - Strip whitespace / excess punctuation
    - Lowercase
    - Remove very common question stopwords (keeps subject terms)
    - Collapse whitespace
    """
    q = query.strip().lower()
    # Remove trailing question marks / periods
    q = q.rstrip("?.!")
    # Expand common abbreviations
    q = re.sub(r"\bpls\b", "please", q)
    q = re.sub(r"\bans\b", "answer", q)
    # Remove stopwords but keep meaningful terms
    words = q.split()
    filtered = [w for w in words if w not in _STOPWORDS]
    # If filtering removed everything, keep original
    result = " ".join(filtered) if filtered else q
    return result


# ─────────────────────────────────────────────────────────────────────
# Retriever
# ─────────────────────────────────────────────────────────────────────

class Retriever:
    """Hybrid retrieval: semantic + keyword search with neighbour expansion.

    Parameters
    ----------
    pg : PostgresHandler
        Connected handler.
    embedder : ChunkEmbedder
        Loaded embedding model.
    semantic_k : int
        Top-k for semantic (vector) search.
    keyword_k : int
        Top-k for keyword (BM25) search.
    neighbour_window : int
        ±N neighbours to expand around each hit.
    """

    def __init__(
        self,
        pg: PostgresHandler,
        embedder: ChunkEmbedder,
        semantic_k: int = DEFAULT_SEMANTIC_K,
        keyword_k: int = DEFAULT_KEYWORD_K,
        neighbour_window: int = NEIGHBOUR_WINDOW,
    ) -> None:
        self._pg = pg
        self._embedder = embedder
        self._semantic_k = semantic_k
        self._keyword_k = keyword_k
        self._window = neighbour_window

    async def retrieve(
        self,
        query: str,
        chapter_id: uuid.UUID,
    ) -> RetrievalResult:
        """Run the full retrieval pipeline.

        1. Normalise query
        2. Embed query
        3. Hybrid search (semantic + keyword)
        4. Neighbour expansion
        5. Fetch linked images

        Returns ``RetrievalResult`` with ordered chunks + images.
        """
        # ── 1. Normalise ────────────────────────────────────────────
        norm_query = normalise_query(query)
        logger.info("Query: '%s' → normalised: '%s'", query, norm_query)

        # ── 2. Embed ────────────────────────────────────────────────
        query_vec = self._embedder.encode([norm_query])[0]

        # ── 3. Hybrid search (Weighted 70/30) ───────────────────────
        # Fetch a larger pool for scoring
        pool_size = 30
        semantic_hits = await self._pg.search_chunks_semantic(
            query_embedding=query_vec,
            chapter_id=chapter_id,
            limit=pool_size,
        )
        keyword_hits = await self._pg.search_chunks_keyword(
            query=norm_query,
            chapter_id=chapter_id,
            limit=pool_size,
        )

        chunk_map: Dict[uuid.UUID, Dict[str, Any]] = {}
        sem_scores: Dict[uuid.UUID, float] = {}
        kwd_scores: Dict[uuid.UUID, float] = {}

        for hit in semantic_hits:
            cid = hit["chunk_id"]
            chunk_map[cid] = hit
            sem_scores[cid] = hit.get("similarity_score", 0.0)

        for hit in keyword_hits:
            cid = hit["chunk_id"]
            if cid not in chunk_map:
                chunk_map[cid] = hit
            kwd_scores[cid] = hit.get("rank", 0.0)

        # Min-max scaling helper
        def _normalize(scores: Dict[uuid.UUID, float]) -> Dict[uuid.UUID, float]:
            if not scores:
                return {}
            vals = list(scores.values())
            min_val, max_val = min(vals), max(vals)
            rng = max_val - min_val
            if rng == 0:
                return {k: 1.0 for k in scores}
            return {k: (v - min_val) / rng for k, v in scores.items()}

        norm_sem = _normalize(sem_scores)
        norm_kwd = _normalize(kwd_scores)

        # Compute hybrid score
        hybrid_list: List[tuple[float, Dict[str, Any]]] = []
        for cid, chunk in chunk_map.items():
            # If a chunk didn't appear in one search, its normalized score is 0
            s = norm_sem.get(cid, 0.0)
            k = norm_kwd.get(cid, 0.0)
            hybrid_score = (0.7 * s) + (0.3 * k)
            hybrid_list.append((hybrid_score, chunk))

        # Sort descending and take top K
        hybrid_list.sort(key=lambda x: x[0], reverse=True)
        top_k = self._semantic_k + self._keyword_k
        merged = [chunk for score, chunk in hybrid_list[:top_k]]
        seen_ids = {c["chunk_id"] for c in merged}

        logger.info(
            "Hybrid Search: %d semantic pool + %d keyword pool → top %d chunks selected",
            len(semantic_hits), len(keyword_hits), len(merged),
        )

        # ── 4. Neighbour expansion ──────────────────────────────────
        positions: set = set()
        for chunk in merged:
            pos = chunk["position_index"]
            for offset in range(-self._window, self._window + 1):
                positions.add(pos + offset)
        # Remove positions already in merged
        existing_positions = {c["position_index"] for c in merged}
        new_positions = [p for p in positions if p >= 0 and p not in existing_positions]

        if new_positions:
            neighbours = await self._pg.get_neighbor_chunks(
                chapter_id=chapter_id,
                positions=new_positions,
            )
            for n in neighbours:
                if n["chunk_id"] not in seen_ids:
                    seen_ids.add(n["chunk_id"])
                    merged.append(n)
            logger.info("Expanded with %d neighbour chunks", len(neighbours))

        # Sort by position_index for reading order
        merged.sort(key=lambda c: c["position_index"])

        # ── 5. Fetch linked images ──────────────────────────────────
        chunk_ids = [c["chunk_id"] for c in merged]
        images = await self._pg.get_images_for_chunks(chunk_ids)
        logger.info("Found %d linked images", len(images))

        return RetrievalResult(
            query_normalised=norm_query,
            chunks=merged,
            images=images,
        )
