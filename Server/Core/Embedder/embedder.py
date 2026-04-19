"""Core orchestrator for the PDF → node → embedding → retrieval pipeline."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from Core.Embedder.parser import FigureCaption, StructuralNode, extract_pdf, split_into_chunks
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler
from Core.Storage.VectorHandler import VectorHandler

logger = logging.getLogger(__name__)

# Regex to identify diagram-only placeholder content
_RE_DIAGRAM_PLACEHOLDER = re.compile(r"^Diagram\s+\d+$", re.IGNORECASE)


class EmbedderError(Exception):
    """Raised for unrecoverable errors inside the Embedder pipeline."""


class Embedder:
    """Pipeline orchestrator for PrepPanda knowledge ingestion and retrieval.

    Parameters
    ----------
    pg : PostgresHandler
        Relational store – nodes, chapters, users.
    vec : VectorHandler
        pgvector store – embeddings + similarity search.
    bucket : BucketHandler
        Object storage – PDF & image uploads.
    llm_client : object
        Any LLM client exposing ``async generate(prompt: str) -> str``.
    embed_model : object
        Embedding model exposing ``async embed(texts: List[str]) -> List[List[float]]``.
    """

    def __init__(
        self,
        pg: PostgresHandler,
        vec: VectorHandler,
        bucket: BucketHandler,
        llm_client: Any,
        embed_model: Any,
    ) -> None:
        self._pg = pg
        self._vec = vec
        self._bucket = bucket
        self._llm = llm_client
        self._embed = embed_model

    # ──────────────────────────────────────────────────────────────────
    # 1. PDF → NODE PIPELINE
    # ──────────────────────────────────────────────────────────────────

    async def process_pdf(
        self,
        chapter_id: str,
        pdf_path: str,
    ) -> List[str]:
        """Parse a PDF into semantic nodes and embed them.

        Returns a list of the created ``node_id`` strings.
        """
        chap_uuid = uuid.UUID(chapter_id)

        raw_text, matched_images = extract_pdf(pdf_path)
        structural_nodes, _ = split_into_chunks(raw_text)

        text_node_ids: List[str] = []
        image_node_ids: List[str] = []

        # ── text nodes ──────────────────────────────────────────────
        for snode in structural_nodes:
            try:
                node_id = await self.create_node(
                    content=snode.full_content(),
                    chapter_id=str(chap_uuid),
                )
                text_node_ids.append(node_id)
            except Exception:
                logger.exception("Skipping bad text chunk (len=%d)", len(snode.content))

        # ── image / diagram nodes ───────────────────────────────────
        # Only images matched to NCERT figure captions (per-page) are
        # kept.  Portraits, decorative elements, etc. were already
        # dropped during extraction.
        for img_bytes, caption in matched_images:
            try:
                image_url = self._upload_image(
                    img_bytes, chapter_id, caption.figure_id, caption.caption
                )
                node_id = await self.create_node(
                    content=caption.full_caption(),
                    chapter_id=str(chap_uuid),
                    image_url=image_url,
                )
                image_node_ids.append(node_id)
                logger.info(
                    "Stored image node Fig %s (%d bytes) → %s",
                    caption.figure_id, len(img_bytes), image_url,
                )
            except Exception:
                logger.exception("Skipping image Fig %s", caption.figure_id)

        # ── bulk embed ALL nodes ────────────────────────────────────
        # Diagram nodes now carry real NCERT captions with semantic
        # value, so they are worth embedding for retrieval.
        await self.embed_nodes(text_node_ids + image_node_ids)

        return text_node_ids + image_node_ids

    # ──────────────────────────────────────────────────────────────────
    # 2. NODE CREATION
    # ──────────────────────────────────────────────────────────────────

    async def create_node(
        self,
        content: str,
        chapter_id: str,
        tags: Optional[List[str]] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """Persist a single node and return its ``node_id`` as a string."""
        node_data: Dict[str, Any] = {
            "chapter_id": uuid.UUID(chapter_id),
            "content": content,
            "tags": tags or [],
            "image_url": image_url,
        }
        row = await self._pg.create_node(node_data)
        return str(row["id"])

    # ──────────────────────────────────────────────────────────────────
    # 3. SINGLE EMBEDDING
    # ──────────────────────────────────────────────────────────────────

    async def embed_node(self, node_id: str, content: str) -> None:
        """Generate an embedding for *content* and store it under *node_id*."""
        vectors = await self._embed.embed([content])
        await self._vec.insert_embedding(uuid.UUID(node_id), vectors[0])

    # ──────────────────────────────────────────────────────────────────
    # 4. BULK EMBEDDING (optimised – small batches)
    # ──────────────────────────────────────────────────────────────────

    async def embed_nodes(self, node_ids: List[str]) -> None:
        """Fetch content for all *node_ids*, embed in batches, and store.

        Splits into batches of ``EMBED_BATCH_SIZE`` to stay within Gemini
        API limits.  Stores each batch immediately so partial failures
        don't lose all progress.  Skips diagram-placeholder nodes.
        """
        EMBED_BATCH_SIZE = 5  # Gemini batchEmbedContents is strict

        if not node_ids:
            return

        uuids = [uuid.UUID(nid) for nid in node_ids]
        nodes = await self._pg.get_nodes_by_ids(uuids)

        texts: List[str] = []
        valid_ids: List[uuid.UUID] = []
        for node in nodes:
            content = (node.get("content") or "").strip()
            # Skip diagram placeholders — no semantic value
            if not content or _RE_DIAGRAM_PLACEHOLDER.match(content):
                continue
            texts.append(content)
            valid_ids.append(node["id"])

        if not texts:
            return

        total = len(texts)
        stored = 0

        for start in range(0, total, EMBED_BATCH_SIZE):
            end = min(start + EMBED_BATCH_SIZE, total)
            batch_texts = texts[start:end]
            batch_ids = valid_ids[start:end]

            try:
                embeddings = await self._embed.embed(batch_texts)
            except Exception:
                logger.exception(
                    "Embed API failed for batch %d–%d, skipping", start, end
                )
                continue

            pairs: List[Tuple[uuid.UUID, List[float]]] = list(
                zip(batch_ids, embeddings)
            )
            try:
                await self._vec.batch_insert_embeddings(pairs)
                stored += len(pairs)
                logger.info(
                    "Embedded batch %d–%d (%d/%d)", start, end, stored, total
                )
            except Exception:
                logger.warning(
                    "Batch insert failed for %d–%d, falling back to individual",
                    start, end,
                )
                for nid, vec in pairs:
                    try:
                        await self._vec.insert_embedding(nid, vec)
                        stored += 1
                    except Exception:
                        logger.exception(
                            "Failed to store embedding for node %s", nid
                        )

        logger.info("Embedding complete: %d/%d stored", stored, total)

    # ──────────────────────────────────────────────────────────────────
    # 5. HYBRID RETRIEVAL CHAIN (vector + keyword, RRF merge)
    # ──────────────────────────────────────────────────────────────────

    async def retrieve(
        self,
        query: str,
        chapter_id: str,
        limit: int = 10,
        diagram_limit: int = 3,
    ) -> Dict[str, Any]:
        """Hybrid retrieve: vector similarity + keyword search merged via RRF.

        Returns a dict with two keys:

        * ``"nodes"`` – top text nodes (full records with ``similarity_score``
          and ``rrf_score``).
        * ``"diagrams"`` – diagram nodes relevant to the query.  Diagrams that
          ranked inside the top results are always included; if fewer than
          *diagram_limit* surfaced naturally, a targeted vector search for
          diagram-only nodes fills the gap.
        """
        chap_uuid = uuid.UUID(chapter_id)

        # ── Vector search ───────────────────────────────────────────
        query_vec = (await self._embed.embed([query]))[0]
        vec_results = await self._vec.search_similar(
            query_vec, chap_uuid, limit=limit * 2
        )

        # ── Keyword search ──────────────────────────────────────────
        kw_results = await self._pg.keyword_search_nodes(
            query, chap_uuid, limit=limit * 2
        )

        # ── Reciprocal Rank Fusion (k=60) ───────────────────────────
        K = 60
        rrf_scores: Dict[uuid.UUID, float] = {}

        for rank, r in enumerate(vec_results):
            nid = r["node_id"]
            rrf_scores[nid] = rrf_scores.get(nid, 0.0) + 1.0 / (K + rank + 1)

        for rank, r in enumerate(kw_results):
            nid = r["id"]
            rrf_scores[nid] = rrf_scores.get(nid, 0.0) + 1.0 / (K + rank + 1)

        if not rrf_scores:
            return {"nodes": [], "diagrams": []}

        # ── Fetch full node records ─────────────────────────────────
        sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[
            : limit + diagram_limit
        ]
        nodes = await self._pg.get_nodes_by_ids(sorted_ids)

        vec_score_map = {r["node_id"]: r["similarity_score"] for r in vec_results}

        for node in nodes:
            nid = node["id"]
            node["similarity_score"] = vec_score_map.get(nid, 0.0)
            node["rrf_score"] = rrf_scores.get(nid, 0.0)

        # ── Split into text vs diagram nodes ────────────────────────
        text_nodes: List[Dict[str, Any]] = []
        diagram_nodes: List[Dict[str, Any]] = []

        for node in nodes:
            if node.get("image_url"):
                diagram_nodes.append(node)
            else:
                text_nodes.append(node)

        text_nodes.sort(key=lambda n: n["rrf_score"], reverse=True)
        diagram_nodes.sort(key=lambda n: n["rrf_score"], reverse=True)

        # ── Fill diagram slots if needed ────────────────────────────
        # If fewer than diagram_limit diagrams surfaced via RRF, do a
        # targeted vector search restricted to diagram nodes.
        if len(diagram_nodes) < diagram_limit:
            existing_ids = {n["id"] for n in diagram_nodes}
            extra = await self._pg.search_diagram_nodes(
                query, chap_uuid, limit=diagram_limit
            )
            for node in extra:
                if node["id"] not in existing_ids:
                    node["similarity_score"] = 0.0
                    node["rrf_score"] = 0.0
                    diagram_nodes.append(node)
                    existing_ids.add(node["id"])
                if len(diagram_nodes) >= diagram_limit:
                    break

        return {
            "nodes": text_nodes[:limit],
            "diagrams": diagram_nodes[:diagram_limit],
        }

    # ──────────────────────────────────────────────────────────────────
    # 6. FILTERING / CRUD HELPERS
    # ──────────────────────────────────────────────────────────────────

    async def get_nodes_by_chapter(self, chapter_id: str) -> List[Dict[str, Any]]:
        """Return all nodes belonging to a chapter."""
        return await self._pg.get_nodes_by_chapter(uuid.UUID(chapter_id))

    async def get_important_nodes(
        self,
        chapter_id: str,
        threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Return nodes whose importance >= *threshold*."""
        all_nodes = await self._pg.get_nodes_by_chapter(uuid.UUID(chapter_id))
        return [n for n in all_nodes if (n.get("importance") or 0.0) >= threshold]

    # ──────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ──────────────────────────────────────────────────────────────────

    def _upload_image(
        self,
        img_bytes: bytes,
        chapter_id: str,
        figure_id: str,
        caption: str,
    ) -> str:
        """Upload diagram bytes to the bucket and return the public URL.

        File is named from the figure caption for readability, e.g.
        ``{chapter_id}/fig_1.1_ls_of_a_flower.png``.
        """
        slug = (
            re.sub(r"[^a-z0-9]+", "_", caption.lower()).strip("_")[:60]
            if caption
            else ""
        )
        name = f"fig_{figure_id}_{slug}" if slug else f"fig_{figure_id}"
        filename = f"{chapter_id}/{name}.png"
        return self._bucket.upload_bytes(img_bytes, filename, "image/png")

    def _upload_pdf(
        self,
        pdf_bytes: bytes,
        chapter_id: str,
        pdf_name: str,
    ) -> str:
        """Upload the source PDF to the bucket and return the public URL."""
        safe_name = pdf_name.replace(" ", "_")
        filename = f"chapters/{chapter_id}/pdf/{safe_name}"
        return self._bucket.upload_bytes(pdf_bytes, filename, "application/pdf")