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

    # ==========================================================
    # CATALOG — user-facing read queries
    # ==========================================================

    async def list_books(
        self,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all books, optionally filtered by grade and/or subject."""
        pool = self._pool_guard()

        clauses: List[str] = []
        params: list = []
        idx = 1

        if grade is not None:
            clauses.append(f"b.grade = ${idx}")
            params.append(grade)
            idx += 1
        if subject is not None:
            clauses.append(f"LOWER(b.subject) = LOWER(${idx})")
            params.append(subject)
            idx += 1

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        rows = await pool.fetch(
            f"""
            SELECT b.*,
                   COUNT(DISTINCT ch.chapter_id) AS chapter_count
            FROM core.books b
            LEFT JOIN core.chapters ch ON ch.book_id = b.book_id
            {where}
            GROUP BY b.book_id
            ORDER BY b.grade, b.subject, b.title
            """,
            *params,
        )
        return [self._record_to_dict(r) for r in rows]

    async def get_book(self, book_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get a single book by ID."""
        pool = self._pool_guard()
        row = await pool.fetchrow(
            "SELECT * FROM core.books WHERE book_id = $1", book_id
        )
        return self._record_to_dict(row) if row else None

    async def list_chapters(
        self, book_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """List all chapters for a book with aggregate counts."""
        pool = self._pool_guard()
        rows = await pool.fetch(
            """
            SELECT ch.*,
                   COALESCE(cs.chunk_count, 0)  AS chunk_count,
                   COALESCE(cs.image_count, 0)  AS image_count,
                   COALESCE(ps.pyq_count, 0)    AS pyq_count
            FROM core.chapters ch
            LEFT JOIN LATERAL (
                SELECT COUNT(*)            AS chunk_count,
                       COUNT(DISTINCT cil.image_id) AS image_count
                FROM core.chunks c
                LEFT JOIN core.chunk_image_links cil ON cil.chunk_id = c.chunk_id
                WHERE c.chapter_id = ch.chapter_id
            ) cs ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS pyq_count
                FROM core.pyqs p
                WHERE p.chapter_id = ch.chapter_id
            ) ps ON TRUE
            WHERE ch.book_id = $1
            ORDER BY ch.chapter_number
            """,
            book_id,
        )
        return [self._record_to_dict(r) for r in rows]

    async def get_chapter(
        self, chapter_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Get a single chapter by ID with aggregate counts."""
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            SELECT ch.*,
                   COALESCE(cs.chunk_count, 0)  AS chunk_count,
                   COALESCE(cs.image_count, 0)  AS image_count,
                   COALESCE(ps.pyq_count, 0)    AS pyq_count
            FROM core.chapters ch
            LEFT JOIN LATERAL (
                SELECT COUNT(*)            AS chunk_count,
                       COUNT(DISTINCT cil.image_id) AS image_count
                FROM core.chunks c
                LEFT JOIN core.chunk_image_links cil ON cil.chunk_id = c.chunk_id
                WHERE c.chapter_id = ch.chapter_id
            ) cs ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS pyq_count
                FROM core.pyqs p
                WHERE p.chapter_id = ch.chapter_id
            ) ps ON TRUE
            WHERE ch.chapter_id = $1
            """,
            chapter_id,
        )
        return self._record_to_dict(row) if row else None

    async def list_pyqs(
        self,
        *,
        book_id: Optional[uuid.UUID] = None,
        chapter_id: Optional[uuid.UUID] = None,
        year: Optional[int] = None,
        exam: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List PYQs with flexible filtering."""
        pool = self._pool_guard()

        clauses: List[str] = []
        params: list = []
        idx = 1

        if book_id is not None:
            clauses.append(f"p.book_id = ${idx}")
            params.append(book_id)
            idx += 1
        if chapter_id is not None:
            clauses.append(f"p.chapter_id = ${idx}")
            params.append(chapter_id)
            idx += 1
        if year is not None:
            clauses.append(f"p.year = ${idx}")
            params.append(year)
            idx += 1
        if exam is not None:
            clauses.append(f"UPPER(p.exam) = UPPER(${idx})")
            params.append(exam)
            idx += 1

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        rows = await pool.fetch(
            f"""
            SELECT p.*
            FROM core.pyqs p
            {where}
            ORDER BY p.year DESC NULLS LAST, p.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params,
            limit,
            offset,
        )
        return [self._record_to_dict(r) for r in rows]

    async def count_pyqs(
        self,
        *,
        book_id: Optional[uuid.UUID] = None,
        chapter_id: Optional[uuid.UUID] = None,
        year: Optional[int] = None,
        exam: Optional[str] = None,
    ) -> int:
        """Count PYQs matching the given filters (for pagination metadata)."""
        pool = self._pool_guard()

        clauses: List[str] = []
        params: list = []
        idx = 1

        if book_id is not None:
            clauses.append(f"book_id = ${idx}")
            params.append(book_id)
            idx += 1
        if chapter_id is not None:
            clauses.append(f"chapter_id = ${idx}")
            params.append(chapter_id)
            idx += 1
        if year is not None:
            clauses.append(f"year = ${idx}")
            params.append(year)
            idx += 1
        if exam is not None:
            clauses.append(f"UPPER(exam) = UPPER(${idx})")
            params.append(exam)
            idx += 1

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        row = await pool.fetchrow(
            f"SELECT COUNT(*) AS cnt FROM core.pyqs {where}", *params
        )
        return row["cnt"]

    async def get_chunks_in_range(
        self,
        chapter_id: uuid.UUID,
        start: int,
        end: int,
    ) -> List[Dict[str, Any]]:
        """Get chunks for a chapter within a position_index range [start, end]."""
        pool = self._pool_guard()
        rows = await pool.fetch(
            """
            SELECT *
            FROM core.chunks
            WHERE chapter_id = $1
              AND position_index >= $2
              AND position_index <= $3
            ORDER BY position_index
            """,
            chapter_id,
            start,
            end,
        )
        return [self._record_to_dict(r) for r in rows]

    async def get_chapter_chunk_bounds(
        self, chapter_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Return min/max position_index and total chunk count for a chapter."""
        pool = self._pool_guard()
        row = await pool.fetchrow(
            """
            SELECT MIN(position_index) AS min_pos,
                   MAX(position_index) AS max_pos,
                   COUNT(*)            AS total
            FROM core.chunks
            WHERE chapter_id = $1
            """,
            chapter_id,
        )
        if not row or row["total"] == 0:
            return None
        return self._record_to_dict(row)

    # ==========================================================
    # PYQ ANALYSIS — bulk data for trend / prediction engine
    # ==========================================================

    async def get_pyq_chunk_analysis(
        self,
        book_id: uuid.UUID,
        chapter_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all PYQ→chunk mappings for analysis in a single round-trip.

        Each row contains the PYQ metadata, the mapped chunk details, and the
        relevance score.  This powers the topic-zone frequency analysis.
        """
        pool = self._pool_guard()

        chapter_filter = ""
        params: list = [book_id]

        if chapter_id is not None:
            chapter_filter = "AND ch.chapter_id = $2"
            params.append(chapter_id)

        rows = await pool.fetch(
            f"""
            SELECT p.pyq_id,
                   p.question,
                   p.answer,
                   p.year,
                   p.exam,
                   p.marks,
                   pcm.chunk_id,
                   pcm.relevance,
                   c.position_index,
                   c.section_title,
                   c.content,
                   ch.chapter_id,
                   ch.title AS chapter_title,
                   ch.chapter_number
            FROM core.pyqs p
            JOIN core.pyq_chunk_map pcm ON pcm.pyq_id = p.pyq_id
            JOIN core.chunks c          ON c.chunk_id  = pcm.chunk_id
            JOIN core.chapters ch       ON ch.chapter_id = c.chapter_id
            WHERE p.book_id = $1
              {chapter_filter}
            ORDER BY ch.chapter_number, c.position_index
            """,
            *params,
        )
        return [self._record_to_dict(r) for r in rows]