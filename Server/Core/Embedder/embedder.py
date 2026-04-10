"""Core orchestrator for the PDF → node → embedding → retrieval pipeline."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from Core.Embedder.parser import StructuralNode, extract_pdf, split_into_chunks
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler
from Core.Storage.VectorHandler import VectorHandler

logger = logging.getLogger(__name__)


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

        raw_text, images = extract_pdf(pdf_path)
        structural_nodes = split_into_chunks(raw_text)
        node_ids: List[str] = []

        # ── text nodes ──────────────────────────────────────────────
        for snode in structural_nodes:
            try:
                node_id = await self.create_node(
                    content=snode.full_content(),
                    chapter_id=str(chap_uuid),
                )
                node_ids.append(node_id)
            except Exception:
                logger.exception("Skipping bad text chunk (len=%d)", len(snode.content))

        # ── image / diagram nodes ───────────────────────────────────
        for idx, img_bytes in enumerate(images):
            try:
                image_url = self._upload_image(img_bytes, chapter_id, idx)
                node_id = await self.create_node(
                    content=f"Diagram {idx + 1}",
                    chapter_id=str(chap_uuid),
                    image_url=image_url,
                )
                node_ids.append(node_id)
                logger.info(
                    "Stored image node #%d (%d bytes) → %s",
                    idx, len(img_bytes), image_url,
                )
            except Exception:
                logger.exception("Skipping image #%d", idx)

        # ── bulk embed ──────────────────────────────────────────────
        await self.embed_nodes(node_ids)

        return node_ids

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
    # 4. BULK EMBEDDING (optimised)
    # ──────────────────────────────────────────────────────────────────

    async def embed_nodes(self, node_ids: List[str]) -> None:
        """Fetch content for all *node_ids*, embed in batches, and store.

        Splits into batches of ``EMBED_BATCH_SIZE`` to stay within API limits
        and stores each batch immediately so partial failures don't lose all
        progress.
        """
        EMBED_BATCH_SIZE = 20  # Gemini batchEmbedContents is reliable at ≤20

        if not node_ids:
            return

        uuids = [uuid.UUID(nid) for nid in node_ids]
        nodes = await self._pg.get_nodes_by_ids(uuids)

        texts: List[str] = []
        valid_ids: List[uuid.UUID] = []
        for node in nodes:
            content = (node.get("content") or "").strip()
            if content:
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
    # 5. RETRIEVAL CHAIN
    # ──────────────────────────────────────────────────────────────────

    async def retrieve(
        self,
        query: str,
        chapter_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Embed the query, search for similar nodes, and return enriched results.

        Each result dict contains the full node record plus a ``similarity_score``.
        """
        query_vec = (await self._embed.embed([query]))[0]
        chap_uuid = uuid.UUID(chapter_id)

        results = await self._vec.search_similar(query_vec, chap_uuid, limit=limit)
        if not results:
            return []

        matched_ids = [r["node_id"] for r in results]
        nodes = await self._pg.get_nodes_by_ids(matched_ids)

        score_map = {r["node_id"]: r["similarity_score"] for r in results}

        enriched: List[Dict[str, Any]] = []
        for node in nodes:
            node["similarity_score"] = score_map.get(node["id"], 0.0)
            enriched.append(node)

        enriched.sort(key=lambda n: n["similarity_score"], reverse=True)
        return enriched

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
        index: int,
    ) -> str:
        """Upload diagram bytes to the bucket and return the public URL."""
        filename = f"chapters/{chapter_id}/diagrams/{index}.png"
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