import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg


class PostgresHandlerError(Exception):
    pass


class PostgresHandler:
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

    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _pool_guard(self) -> asyncpg.Pool:
        if not self._pool:
            raise PostgresHandlerError("Pool not initialised. Call connect() first.")
        return self._pool

    @staticmethod
    def _record_to_dict(record: asyncpg.Record) -> Dict[str, Any]:
        return dict(record)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def create_user(self, email: str) -> Dict[str, Any]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            INSERT INTO core.users (id, email, created_at)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            uuid.uuid4(),
            email,
            datetime.utcnow(),
        )
        return self._record_to_dict(row)

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            "SELECT * FROM core.users WHERE id = $1",
            user_id,
        )
        return self._record_to_dict(row) if row else None

    # ------------------------------------------------------------------
    # Chapters
    # ------------------------------------------------------------------

    async def create_chapter(
        self,
        title: str,
        subject: str,
        pdf_url: str,
    ) -> Dict[str, Any]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            INSERT INTO core.chapters (id, title, subject, pdf_url, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            uuid.uuid4(),
            title,
            subject,
            pdf_url,
            datetime.utcnow(),
        )
        return self._record_to_dict(row)

    async def get_chapter(self, chapter_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            "SELECT * FROM core.chapters WHERE id = $1",
            chapter_id,
        )
        return self._record_to_dict(row) if row else None

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    async def create_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        node_data keys:
            chapter_id (UUID), content (str), type (str),
            tags (List[str]), importance (float),
            image_url (str | None)
        """
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            INSERT INTO core.nodes
                (id, chapter_id, content, type, tags, importance, image_url, created_at)
            VALUES ($1, $2, $3, $4::core.node_type, $5, $6, $7, $8)
            RETURNING *
            """,
            uuid.uuid4(),
            node_data["chapter_id"],
            node_data["content"],
            node_data["type"],
            node_data.get("tags", []),
            node_data.get("importance", 0.0),
            node_data.get("image_url"),
            datetime.utcnow(),
        )
        return self._record_to_dict(row)

    async def get_node(self, node_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            "SELECT * FROM core.nodes WHERE id = $1",
            node_id,
        )
        return self._record_to_dict(row) if row else None

    async def get_nodes_by_chapter(self, chapter_id: uuid.UUID) -> List[Dict[str, Any]]:
        pool = self._pool_guard()
        rows = await pool.fetch(
            "SELECT * FROM core.nodes WHERE chapter_id = $1 ORDER BY created_at",
            chapter_id,
        )
        return [self._record_to_dict(r) for r in rows]

    async def get_nodes_by_ids(self, node_ids: List[uuid.UUID]) -> List[Dict[str, Any]]:
        if not node_ids:
            return []
        pool = self._pool_guard()
        rows = await pool.fetch(
            "SELECT * FROM core.nodes WHERE id = ANY($1::uuid[])",
            node_ids,
        )
        return [self._record_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # User Progress
    # ------------------------------------------------------------------

    async def update_progress(
        self,
        user_id: uuid.UUID,
        node_id: uuid.UUID,
        accuracy_delta: float,
    ) -> Dict[str, Any]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            INSERT INTO core.user_progress (user_id, node_id, accuracy, attempts)
            VALUES ($1, $2, $3, 1)
            ON CONFLICT (user_id, node_id) DO UPDATE
                SET accuracy  = (core.user_progress.accuracy * core.user_progress.attempts + $3)
                                 / (core.user_progress.attempts + 1),
                    attempts   = core.user_progress.attempts + 1
            RETURNING *
            """,
            user_id,
            node_id,
            accuracy_delta,
        )
        return self._record_to_dict(row)

    async def get_user_progress(
        self,
        user_id: uuid.UUID,
        chapter_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        pool = self._pool_guard()
        rows = await pool.fetch(
            """
            SELECT up.*
            FROM core.user_progress up
            JOIN core.nodes n ON n.id = up.node_id
            WHERE up.user_id = $1
              AND n.chapter_id = $2
            """,
            user_id,
            chapter_id,
        )
        return [self._record_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Chat History
    # ------------------------------------------------------------------

    async def save_chat(
        self,
        user_id: uuid.UUID,
        chapter_id: uuid.UUID,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        import json

        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            INSERT INTO core.chat_history (id, user_id, chapter_id, messages, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            RETURNING *
            """,
            uuid.uuid4(),
            user_id,
            chapter_id,
            json.dumps(messages),
            datetime.utcnow(),
        )
        return self._record_to_dict(row)

    async def get_chat_history(
        self,
        user_id: uuid.UUID,
        chapter_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        pool = self._pool_guard()
        rows = await pool.fetch(
            """
            SELECT * FROM core.chat_history
            WHERE user_id = $1 AND chapter_id = $2
            ORDER BY created_at
            """,
            user_id,
            chapter_id,
        )
        return [self._record_to_dict(r) for r in rows]
