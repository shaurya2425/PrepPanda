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

        # ── 3. Hybrid search ────────────────────────────────────────
        semantic_hits = await self._pg.search_chunks_semantic(
            query_embedding=query_vec,
            chapter_id=chapter_id,
            limit=self._semantic_k,
        )
        keyword_hits = await self._pg.search_chunks_keyword(
            query=norm_query,
            chapter_id=chapter_id,
            limit=self._keyword_k,
        )

        # Merge & deduplicate, preserving order (semantic first)
        seen_ids: set = set()
        merged: List[Dict[str, Any]] = []
        for chunk in semantic_hits + keyword_hits:
            cid = chunk["chunk_id"]
            if cid not in seen_ids:
                seen_ids.add(cid)
                merged.append(chunk)

        logger.info(
            "Search: %d semantic + %d keyword → %d unique chunks",
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
