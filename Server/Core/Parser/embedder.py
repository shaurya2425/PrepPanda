"""Chunk embedding module.

Uses ``sentence-transformers`` with the open-source
``all-mpnet-base-v2`` model (768-dim) to embed text chunks and
persist the vectors into ``core.chunks.embedding`` via
``PostgresHandler.update_chunk_embedding``.

Usage
-----
::

    from Core.Parser.embedder import ChunkEmbedder

    embedder = ChunkEmbedder()                       # loads model once
    await embedder.embed_chunks(pg, chunk_records)    # batch embed + store
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

from Core.Storage.PostgresHandler import PostgresHandler

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────────────────

# all-mpnet-base-v2: 768 dims, best quality among small open models.
# Matches the schema's vector(768).
DEFAULT_MODEL = "all-mpnet-base-v2"
DEFAULT_BATCH_SIZE = 32


# ─────────────────────────────────────────────────────────────────────
# Embedder
# ─────────────────────────────────────────────────────────────────────

class ChunkEmbedder:
    """Embeds text chunks and stores vectors in PostgreSQL.

    Parameters
    ----------
    model_name : str
        HuggingFace sentence-transformers model identifier.
    batch_size : int
        Number of texts encoded per forward pass.
    device : str or None
        Torch device (``"cpu"``, ``"cuda"``). ``None`` = auto-detect.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
        device: Optional[str] = None,
    ) -> None:
        logger.info("Loading embedding model '%s' …", model_name)
        self._model = SentenceTransformer(model_name, device=device)
        self._batch_size = batch_size
        self._dim = self._model.get_sentence_embedding_dimension()
        logger.info(
            "Model loaded: dim=%d, device=%s",
            self._dim, self._model.device,
        )

    @property
    def dim(self) -> int:
        """Embedding dimension (e.g. 768)."""
        return self._dim

    # ─────────────────────────────────────────────────────────────────
    # Core: encode texts
    # ─────────────────────────────────────────────────────────────────

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of texts into embedding vectors.

        Returns a list of float lists (one per text).
        """
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=len(texts) > self._batch_size,
            normalize_embeddings=True,
        )
        # Convert numpy arrays to plain lists for DB storage
        return [vec.tolist() for vec in embeddings]

    # ─────────────────────────────────────────────────────────────────
    # DB integration: embed + update existing chunks
    # ─────────────────────────────────────────────────────────────────

    async def embed_chunks(
        self,
        pg: PostgresHandler,
        chunk_records: List[Dict[str, Any]],
    ) -> int:
        """Embed chunk content and write vectors to the DB.

        Parameters
        ----------
        pg : PostgresHandler
            Connected handler.
        chunk_records : list[dict]
            Entries from ``ChapterPipeline._store_chunks`` — each dict
            has ``"db"`` (DB row with ``chunk_id``, ``content``) and
            ``"tc"`` (TextChunk).

        Returns
        -------
        int
            Number of chunks successfully embedded.
        """
        if not chunk_records:
            return 0

        # Prepare texts — use full_content() for section-prefixed text
        # if available, otherwise fall back to raw content.
        texts: List[str] = []
        chunk_ids: List[uuid.UUID] = []

        for entry in chunk_records:
            tc = entry.get("tc")
            db = entry["db"]
            if tc and hasattr(tc, "full_content"):
                texts.append(tc.full_content())
            else:
                texts.append(db["content"])
            chunk_ids.append(db["chunk_id"])

        # Encode in batch
        logger.info("Encoding %d chunks …", len(texts))
        vectors = self.encode(texts)

        # Write to DB
        count = 0
        for chunk_id, vec in zip(chunk_ids, vectors):
            try:
                await pg.update_chunk_embedding(chunk_id, vec)
                count += 1
            except Exception as e:
                logger.warning(
                    "Failed to update embedding for chunk %s: %s",
                    chunk_id, e,
                )

        logger.info("Embeddings stored: %d / %d", count, len(chunk_records))
        return count
