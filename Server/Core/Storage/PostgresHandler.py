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

    @staticmethod
    def _embedding_to_pg(embedding: List[float]) -> str:
        return "[" + ",".join(str(v) for v in embedding) + "]"

    # ==========================================================
    # BOOKS
    # ==========================================================

    async def create_book(self, title: str, grade: int, subject: str) -> Dict[str, Any]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            INSERT INTO core.books (book_id, title, grade, subject, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            uuid.uuid4(),
            title,
            grade,
            subject,
            datetime.utcnow(),
        )
        return self._record_to_dict(row)

    # ==========================================================
    # CHAPTERS
    # ==========================================================

    async def create_chapter(
        self,
        book_id: uuid.UUID,
        chapter_number: int,
        title: str,
        pdf_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            INSERT INTO core.chapters (chapter_id, book_id, chapter_number, title, pdf_url, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            uuid.uuid4(),
            book_id,
            chapter_number,
            title,
            pdf_url,
            datetime.utcnow(),
        )
        return self._record_to_dict(row)

    async def update_chapter_pdf_url(
        self,
        chapter_id: uuid.UUID,
        pdf_url: str,
    ) -> None:
        """Set (or overwrite) the pdf_url for an existing chapter."""
        pool = self._pool_guard()
        await pool.execute(
            "UPDATE core.chapters SET pdf_url = $2 WHERE chapter_id = $1",
            chapter_id,
            pdf_url,
        )

    # ==========================================================
    # CHUNKS (CORE)
    # ==========================================================

    async def create_chunk(
        self,
        chapter_id: uuid.UUID,
        content: str,
        token_count: int,
        position_index: int,
        embedding: List[float],
        section_title: Optional[str] = None,
        pyq_score: float = 0.0,
    ) -> Dict[str, Any]:
        pool = self._pool_guard()

        row = await pool.fetchrow(
            """
            INSERT INTO core.chunks
            (chunk_id, chapter_id, content, token_count, position_index,
             section_title, tsv, embedding, created_at, pyq_score)
            VALUES (
                $1, $2, $3, $4, $5,
                $6,
                to_tsvector('english', $3),
                $7::vector,
                $8, $9
            )
            RETURNING *
            """,
            uuid.uuid4(),
            chapter_id,
            content,
            token_count,
            position_index,
            section_title,
            self._embedding_to_pg(embedding),
            datetime.utcnow(),
            pyq_score,
        )

        return self._record_to_dict(row)

    async def get_chunks_by_ids(
        self, chunk_ids: List[uuid.UUID]
    ) -> List[Dict[str, Any]]:
        if not chunk_ids:
            return []

        pool = self._pool_guard()
        rows = await pool.fetch(
            """
            SELECT *
            FROM core.chunks
            WHERE chunk_id = ANY($1::uuid[])
            """,
            chunk_ids,
        )
        return [self._record_to_dict(r) for r in rows]

    async def update_chunk_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
    ) -> None:
        """Update the embedding vector for an existing chunk."""
        pool = self._pool_guard()
        await pool.execute(
            """
            UPDATE core.chunks
            SET embedding = $2::vector
            WHERE chunk_id = $1
            """,
            chunk_id,
            self._embedding_to_pg(embedding),
        )

    # ==========================================================
    # SEMANTIC SEARCH
    # ==========================================================

    async def search_chunks_semantic(
        self,
        query_embedding: List[float],
        chapter_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        pool = self._pool_guard()

        rows = await pool.fetch(
            """
            SELECT *,
                   1 - (embedding <=> $1::vector) AS similarity_score
            FROM core.chunks
            WHERE chapter_id = $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            self._embedding_to_pg(query_embedding),
            chapter_id,
            limit,
        )

        return [self._record_to_dict(r) for r in rows]

    # ==========================================================
    # KEYWORD SEARCH (BM25-ish)
    # ==========================================================

    async def search_chunks_keyword(
        self,
        query: str,
        chapter_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        pool = self._pool_guard()

        rows = await pool.fetch(
            """
            SELECT *,
                   ts_rank_cd(tsv, plainto_tsquery('english', $1)) AS rank
            FROM core.chunks
            WHERE chapter_id = $2
              AND tsv @@ plainto_tsquery('english', $1)
            ORDER BY rank DESC
            LIMIT $3
            """,
            query,
            chapter_id,
            limit,
        )

        return [self._record_to_dict(r) for r in rows]

    # ==========================================================
    # NEIGHBOR EXPANSION
    # ==========================================================

    async def get_neighbor_chunks(
        self,
        chapter_id: uuid.UUID,
        positions: List[int],
    ) -> List[Dict[str, Any]]:
        pool = self._pool_guard()

        rows = await pool.fetch(
            """
            SELECT *
            FROM core.chunks
            WHERE chapter_id = $1
              AND position_index = ANY($2::int[])
            """,
            chapter_id,
            positions,
        )

        return [self._record_to_dict(r) for r in rows]

    # ==========================================================
    # IMAGES
    # ==========================================================

    async def create_image(
        self,
        chapter_id: uuid.UUID,
        image_path: str,
        caption: Optional[str],
        position_index: int,
    ) -> Dict[str, Any]:
        pool = self._pool_guard()

        row = await pool.fetchrow(
            """
            INSERT INTO core.images
            (image_id, chapter_id, image_path, caption, position_index, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            uuid.uuid4(),
            chapter_id,
            image_path,
            caption,
            position_index,
            datetime.utcnow(),
        )

        return self._record_to_dict(row)

    async def link_chunk_image(
        self,
        chunk_id: uuid.UUID,
        image_id: uuid.UUID,
    ) -> None:
        pool = self._pool_guard()

        await pool.execute(
            """
            INSERT INTO core.chunk_image_links (chunk_id, image_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            chunk_id,
            image_id,
        )

    async def get_images_for_chunks(
        self,
        chunk_ids: List[uuid.UUID],
    ) -> List[Dict[str, Any]]:
        if not chunk_ids:
            return []

        pool = self._pool_guard()

        rows = await pool.fetch(
            """
            SELECT i.*, cil.chunk_id
            FROM core.chunk_image_links cil
            JOIN core.images i ON i.image_id = cil.image_id
            WHERE cil.chunk_id = ANY($1::uuid[])
            """,
            chunk_ids,
        )

        return [self._record_to_dict(r) for r in rows]

    # ==========================================================
    # PYQs
    # ==========================================================

    async def create_pyq(
        self,
        book_id: uuid.UUID,
        question: str,
        answer: Optional[str] = None,
        chapter_id: Optional[uuid.UUID] = None,
        year: Optional[int] = None,
        exam: Optional[str] = None,
        marks: Optional[int] = None,
    ) -> Dict[str, Any]:
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            INSERT INTO core.pyqs (
                pyq_id, book_id, chapter_id, question, answer,
                year, exam, marks, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            uuid.uuid4(),
            book_id,
            chapter_id,
            question,
            answer,
            year,
            exam,
            marks,
            datetime.utcnow(),
        )
        return self._record_to_dict(row)

    async def update_pyq_chapter(
        self,
        pyq_id: uuid.UUID,
        chapter_id: uuid.UUID,
    ) -> None:
        """Assign a chapter to a PYQ after semantic mapping."""
        pool = self._pool_guard()
        await pool.execute(
            "UPDATE core.pyqs SET chapter_id = $1 WHERE pyq_id = $2",
            chapter_id, pyq_id,
        )

    async def link_pyq_chunk(
        self,
        pyq_id: uuid.UUID,
        chunk_id: uuid.UUID,
        relevance: float = 1.0,
    ) -> None:
        pool = self._pool_guard()
        await pool.execute(
            """
            INSERT INTO core.pyq_chunk_map (pyq_id, chunk_id, relevance)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            pyq_id,
            chunk_id,
            relevance,
        )

    async def get_pyqs_for_chunks(
        self,
        chunk_ids: List[uuid.UUID],
    ) -> List[Dict[str, Any]]:
        if not chunk_ids:
            return []

        pool = self._pool_guard()
        rows = await pool.fetch(
            """
            SELECT p.*, pcm.chunk_id, pcm.relevance
            FROM core.pyq_chunk_map pcm
            JOIN core.pyqs p ON p.pyq_id = pcm.pyq_id
            WHERE pcm.chunk_id = ANY($1::uuid[])
            """,
            chunk_ids,
        )

        return [self._record_to_dict(r) for r in rows]