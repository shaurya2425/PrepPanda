"""Catalog router — public, user-facing read endpoints.

These routes do **not** require the ``X-Admin-Key`` header.

Endpoints
---------
GET /catalog/books
    List all available books.  Optional ``grade`` and ``subject`` query filters.

GET /catalog/books/{book_id}
    Get a single book with its list of chapters.

GET /catalog/books/{book_id}/chapters
    List chapters for a book (with chunk / image / PYQ counts).

GET /catalog/chapters/{chapter_id}
    Get a single chapter detail (with counts).

GET /catalog/chapters/{chapter_id}/pyqs
    List PYQs mapped to a chapter (paginated, filterable by year/exam).

GET /catalog/books/{book_id}/pyqs
    List PYQs for an entire book (paginated, filterable by year/exam).
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from Routers.deps import PgDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog", tags=["catalog"])


# ─────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────

class BookListItem(BaseModel):
    book_id: uuid.UUID
    title: str
    grade: int
    subject: str
    chapter_count: int


class ChapterListItem(BaseModel):
    chapter_id: uuid.UUID
    book_id: uuid.UUID
    chapter_number: int
    title: str
    pdf_url: Optional[str] = None
    chunk_count: int
    image_count: int
    pyq_count: int


class BookDetail(BaseModel):
    book_id: uuid.UUID
    title: str
    grade: int
    subject: str
    chapters: List[ChapterListItem]


class ChapterDetail(BaseModel):
    chapter_id: uuid.UUID
    book_id: uuid.UUID
    chapter_number: int
    title: str
    pdf_url: Optional[str] = None
    chunk_count: int
    image_count: int
    pyq_count: int


class PYQItem(BaseModel):
    pyq_id: uuid.UUID
    book_id: uuid.UUID
    chapter_id: Optional[uuid.UUID] = None
    question: str
    answer: Optional[str] = None
    year: Optional[int] = None
    exam: Optional[str] = None
    marks: Optional[int] = None


class PYQListOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[PYQItem]


# ─────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────

# ── Books ────────────────────────────────────────────────────────────

@router.get(
    "/books",
    response_model=List[BookListItem],
    summary="List all available books",
)
async def list_books(
    pg: PgDep,
    grade: Optional[int] = Query(None, ge=1, le=12, description="Filter by grade"),
    subject: Optional[str] = Query(None, description="Filter by subject (case-insensitive)"),
) -> List[BookListItem]:
    """
    Return every book in the library.

    Supports optional query-string filters:
    - ``grade`` — integer 1–12
    - ``subject`` — case-insensitive match (e.g. ``biology``)

    Each item includes a ``chapter_count`` for quick UI display.
    """
    rows = await pg.list_books(grade=grade, subject=subject)
    return [BookListItem(**r) for r in rows]


@router.get(
    "/books/{book_id}",
    response_model=BookDetail,
    summary="Get a single book with its chapters",
)
async def get_book(
    book_id: uuid.UUID,
    pg: PgDep,
) -> BookDetail:
    """Return a book and its full chapter listing (with counts)."""
    book = await pg.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found.")

    chapters = await pg.list_chapters(book_id)

    return BookDetail(
        book_id=book["book_id"],
        title=book["title"],
        grade=book["grade"],
        subject=book["subject"],
        chapters=[ChapterListItem(**ch) for ch in chapters],
    )


# ── Chapters ─────────────────────────────────────────────────────────

@router.get(
    "/books/{book_id}/chapters",
    response_model=List[ChapterListItem],
    summary="List chapters for a book",
)
async def list_chapters(
    book_id: uuid.UUID,
    pg: PgDep,
) -> List[ChapterListItem]:
    """List all chapters for the given book, ordered by chapter number."""
    book = await pg.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found.")

    rows = await pg.list_chapters(book_id)
    return [ChapterListItem(**r) for r in rows]


@router.get(
    "/chapters/{chapter_id}",
    response_model=ChapterDetail,
    summary="Get chapter detail",
)
async def get_chapter(
    chapter_id: uuid.UUID,
    pg: PgDep,
) -> ChapterDetail:
    """Get full details for a single chapter, including chunk/image/PYQ counts."""
    ch = await pg.get_chapter(chapter_id)
    if not ch:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found.")
    return ChapterDetail(**ch)


# ── PYQs ─────────────────────────────────────────────────────────────

@router.get(
    "/books/{book_id}/pyqs",
    response_model=PYQListOut,
    summary="List PYQs for a book",
)
async def list_book_pyqs(
    book_id: uuid.UUID,
    pg: PgDep,
    year: Optional[int] = Query(None, description="Filter by exam year"),
    exam: Optional[str] = Query(None, description="Filter by exam board (CBSE, NEET, JEE …)"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> PYQListOut:
    """
    Paginated list of PYQs across all chapters of a book.

    Supports optional filters:
    - ``year`` — exact year match
    - ``exam`` — case-insensitive exam board match
    """
    book = await pg.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found.")

    total = await pg.count_pyqs(book_id=book_id, year=year, exam=exam)
    items = await pg.list_pyqs(
        book_id=book_id, year=year, exam=exam, limit=limit, offset=offset
    )

    return PYQListOut(
        total=total,
        limit=limit,
        offset=offset,
        items=[PYQItem(**r) for r in items],
    )


@router.get(
    "/chapters/{chapter_id}/pyqs",
    response_model=PYQListOut,
    summary="List PYQs for a chapter",
)
async def list_chapter_pyqs(
    chapter_id: uuid.UUID,
    pg: PgDep,
    year: Optional[int] = Query(None, description="Filter by exam year"),
    exam: Optional[str] = Query(None, description="Filter by exam board (CBSE, NEET, JEE …)"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> PYQListOut:
    """Paginated list of PYQs mapped to a specific chapter."""
    ch = await pg.get_chapter(chapter_id)
    if not ch:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found.")

    total = await pg.count_pyqs(chapter_id=chapter_id, year=year, exam=exam)
    items = await pg.list_pyqs(
        chapter_id=chapter_id, year=year, exam=exam, limit=limit, offset=offset
    )

    return PYQListOut(
        total=total,
        limit=limit,
        offset=offset,
        items=[PYQItem(**r) for r in items],
    )
