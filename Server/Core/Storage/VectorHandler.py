import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg


class VectorHandlerError(Exception):
    pass


class VectorHandler:
    def __init__(self) -> None:
        self._dsn = (
            os.environ.get("DATABASE_URL")
            or (
                f"postgresql://{os.environ['POSTGRES_USER']}:"
                f"{os.environ['POSTGRES_PASSWORD']}@"
                f"{os.environ.get('POSTGRES_HOST', 'localhost')}:"
                f"{os.environ.get('POSTGRES_PORT', '5432')}/"
                f"{os.environ['POSTGRES_DB']}"
            )
        )
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _pool_guard(self) -> asyncpg.Pool:
        if not self._pool:
            raise VectorHandlerError("Pool not initialised. Call connect() first.")
        return self._pool

    @staticmethod
    def _embedding_to_pg(embedding: List[float]) -> str:
        """Serialize a float list to pgvector literal: '[0.1,0.2,...]'"""
        return "[" + ",".join(str(v) for v in embedding) + "]"

    # ------------------------------------------------------------------
    # Insert
    # ------------------------------------------------------------------

    async def insert_embedding(
        self,
        node_id: uuid.UUID,
        embedding: List[float],
    ) -> None:
        pool = self._pool_guard()
        await pool.execute(
            """
            INSERT INTO vector.embeddings (node_id, embedding, created_at)
            VALUES ($1, $2::vector, $3)
            ON CONFLICT (node_id) DO UPDATE
                SET embedding   = EXCLUDED.embedding,
                    created_at  = EXCLUDED.created_at
            """,
            node_id,
            self._embedding_to_pg(embedding),
            datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_similar(
        self,
        query_embedding: List[float],
        chapter_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of dicts: [{node_id, similarity_score}, ...]
        Filtered to nodes belonging to chapter_id, ordered by cosine similarity.
        """
        pool = self._pool_guard()
        rows = await pool.fetch(
            """
            SELECT
                e.node_id,
                1 - (e.embedding <=> $1::vector) AS similarity_score
            FROM vector.embeddings e
            JOIN core.nodes n ON n.id = e.node_id
            WHERE n.chapter_id = $2
            ORDER BY e.embedding <=> $1::vector
            LIMIT $3
            """,
            self._embedding_to_pg(query_embedding),
            chapter_id,
            limit,
        )
        return [{"node_id": r["node_id"], "similarity_score": r["similarity_score"]} for r in rows]

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_embedding(self, node_id: uuid.UUID) -> bool:
        pool = self._pool_guard()
        result = await pool.execute(
            "DELETE FROM vector.embeddings WHERE node_id = $1",
            node_id,
        )
        return result == "DELETE 1"
