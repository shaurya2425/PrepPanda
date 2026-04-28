"""Admin router — protected data-ingestion endpoints.

All routes require the ``X-Admin-Key`` header to match ``ADMIN_API_KEY``.

Endpoints
---------
POST /admin/books
    Create a new book entry.

POST /admin/books/{book_id}/chapters
    Upload a chapter PDF and run the full ingestion pipeline:
    NodeParser → VisualParser → embeddings → S3 → Postgres.

POST /admin/books/{book_id}/chapters/{chapter_id}/pyqs
    Bulk-ingest PYQ blocks. Accepts raw text in the block format::

        ---Q <marks>M <year>
        <question text (may be multi-line)>
        ---

        ---Ans
        <answer text (may be multi-line)>
        ---

    One or more such paired blocks make up the request body.
    Questions without a matching answer block are stored with
    ``answer = None``.

POST /admin/books/{book_id}/chapters/{chapter_id}/pyqs/file
    Same as above but accepts a plain-text file upload instead of
    raw body text.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from Core.Parser.chapter_pipeline import ChapterPipeline
from Routers.deps import AdminDep, BucketDep, EmbedDep, PgDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ─────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────

class BookIn(BaseModel):
    title: str   = Field(..., example="Biology Part I – Class XI")
    grade: int   = Field(..., ge=1, le=12, example=11)
    subject: str = Field(..., example="biology")


class BookOut(BaseModel):
    book_id: uuid.UUID
    title: str
    grade: int
    subject: str


class ChapterOut(BaseModel):
    chapter_id:     uuid.UUID
    chapter_number: int
    title: str
    pdf_url:        Optional[str] = None
    chunk_count:    int
    image_count:    int
    link_count:     int
    embedded_count: int


class PYQBlock(BaseModel):
    """One parsed PYQ entry extracted from the block format."""
    question: str
    answer:   Optional[str] = None
    marks:    Optional[int] = None
    year:     Optional[int] = None
    exam:     Optional[str] = None


class PYQIngestOut(BaseModel):
    inserted: int
    skipped:  int
    pyq_ids:  List[uuid.UUID]


# ─────────────────────────────────────────────────────────────────────
# PYQ block format parser
# ─────────────────────────────────────────────────────────────────────
#
# Expected format (one or many blocks per request):
#
#   ---Q 5M 2022
#   What is double fertilisation?
#   ---
#
#   ---Ans
#   Double fertilisation is the process …
#   ---
#
# Rules:
#   • A Q-block header: "---Q" followed by optional "<N>M" (marks) and
#     optional "<YYYY>" (year).  These tokens may appear in any order on
#     the same line and are both optional.
#   • A Q-block body ends at the next bare "---" line.
#   • An Ans-block (optional) immediately follows its Q-block.
#   • Blocks separated by blank lines are fine.

_RE_Q_HEADER = re.compile(
    r"^---Q\b(.*)?$",
    re.IGNORECASE,
)
_RE_ANS_HEADER = re.compile(r"^---Ans\b", re.IGNORECASE)
_RE_BLOCK_END  = re.compile(r"^---\s*$")
_RE_MARKS      = re.compile(r"\b(\d+)\s*[Mm]\b")
_RE_YEAR       = re.compile(r"\b(20\d{2}|19\d{2})\b")
_RE_EXAM       = re.compile(r"\b(CBSE|NEET|JEE|AIIMS|CUET)\b", re.IGNORECASE)


def _parse_q_header(header_rest: str) -> dict:
    """Extract marks, year, exam from the Q-header tail."""
    meta: dict = {}
    m = _RE_MARKS.search(header_rest)
    if m:
        meta["marks"] = int(m.group(1))
    m = _RE_YEAR.search(header_rest)
    if m:
        meta["year"] = int(m.group(1))
    m = _RE_EXAM.search(header_rest)
    if m:
        meta["exam"] = m.group(1).upper()
    return meta


def parse_pyq_blocks(raw: str) -> List[PYQBlock]:
    """Parse raw PYQ text into a list of ``PYQBlock`` objects.

    The parser is lenient:
    - Extra blank lines between / within blocks are ignored.
    - An answer block is matched to the Q-block immediately preceding it.
    - Q-blocks without a following answer block get ``answer = None``.
    """
    lines = raw.splitlines()
    blocks: List[PYQBlock] = []

    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].rstrip()

        # ── Find Q-block header ──────────────────────────────────────
        m_q = _RE_Q_HEADER.match(line)
        if not m_q:
            i += 1
            continue

        header_rest = m_q.group(1) or ""
        meta = _parse_q_header(header_rest)
        i += 1

        # ── Collect Q-block body ─────────────────────────────────────
        q_lines: List[str] = []
        while i < n and not _RE_BLOCK_END.match(lines[i]):
            q_lines.append(lines[i])
            i += 1
        i += 1  # skip closing ---

        question = "\n".join(q_lines).strip()
        if not question:
            continue

        # ── Look ahead for Ans block (skip blank lines) ──────────────
        j = i
        while j < n and not lines[j].strip():
            j += 1

        answer: Optional[str] = None
        if j < n and _RE_ANS_HEADER.match(lines[j].rstrip()):
            i = j + 1
            ans_lines: List[str] = []
            while i < n and not _RE_BLOCK_END.match(lines[i]):
                ans_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ---
            answer = "\n".join(ans_lines).strip() or None

        blocks.append(PYQBlock(
            question=question,
            answer=answer,
            marks=meta.get("marks"),
            year=meta.get("year"),
            exam=meta.get("exam"),
        ))

    return blocks


# ─────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────

# ── Books ────────────────────────────────────────────────────────────

@router.post(
    "/books",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new book",
)
async def create_book(
    body: BookIn,
    pg: PgDep,
    _admin: AdminDep,
) -> BookOut:
    """Create a new book record in ``core.books``."""
    rec = await pg.create_book(
        title=body.title,
        grade=body.grade,
        subject=body.subject,
    )
    return BookOut(**rec)


# ── Chapters ─────────────────────────────────────────────────────────

@router.post(
    "/books/{book_id}/chapters",
    response_model=ChapterOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & ingest a chapter PDF",
)
async def ingest_chapter(
    book_id: uuid.UUID,
    pg: PgDep,
    bucket: BucketDep,
    embedder: EmbedDep,
    _admin: AdminDep,
    chapter_number: Annotated[int, Form(...)] ,
    chapter_title:  Annotated[str, Form(...)],
    pdf: UploadFile = File(..., description="Chapter PDF file"),
) -> ChapterOut:
    """
    Upload a chapter PDF and run the full ingestion pipeline:

    - NodeParser (text chunks + figure refs)
    - VisualParser (figures → S3)
    - ChunkEmbedder (sentence-transformer embeddings)
    - Store everything in Postgres

    Returns counts for chunks, images, and chunk-image links.
    """
    # Validate book exists
    pool = pg._pool_guard()
    book_row = await pool.fetchrow(
        "SELECT book_id FROM core.books WHERE book_id = $1", book_id
    )
    if not book_row:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found.")

    # Save uploaded PDF to a temp path; also keep raw bytes for bucket upload
    import tempfile, os, shutil
    suffix = os.path.splitext(pdf.filename or "chapter.pdf")[1] or ".pdf"
    pdf_bytes = await pdf.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        pipeline = ChapterPipeline(pg=pg, bucket=bucket, embedder=embedder)
        result = await pipeline.ingest(
            pdf_path=tmp_path,
            book_id=book_id,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            pdf_bytes=pdf_bytes,
        )
    except Exception as exc:
        logger.exception("Chapter ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")
    finally:
        os.unlink(tmp_path)

    return ChapterOut(
        chapter_id=result.chapter_id,
        chapter_number=chapter_number,
        title=chapter_title,
        pdf_url=result.pdf_url,
        chunk_count=result.chunk_count,
        image_count=result.image_count,
        link_count=result.link_count,
        embedded_count=result.embedded_count,
    )


# ── PYQs — raw body ──────────────────────────────────────────────────

@router.post(
    "/books/{book_id}/chapters/{chapter_id}/pyqs",
    response_model=PYQIngestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest PYQ blocks (raw text body)",
)
async def ingest_pyqs_text(
    book_id: uuid.UUID,
    chapter_id: uuid.UUID,
    pg: PgDep,
    _admin: AdminDep,
    body: str = Form(
        ...,
        description=(
            "PYQ blocks in the canonical block format:\n\n"
            "---Q 5M 2022\n"
            "Question text\n"
            "---\n\n"
            "---Ans\n"
            "Answer text\n"
            "---"
        ),
    ),
) -> PYQIngestOut:
    """
    Ingest one or more PYQ blocks submitted as form text.

    **Block format** (repeat as many times as needed):

    ```
    ---Q <marks>M <year>
    <question text — may be multi-line>
    ---

    ---Ans
    <answer text — may be multi-line>
    ---
    ```

    - `<marks>M` and `<year>` are both **optional**.
    - An answer block is optional per question.
    - Exam name (CBSE / NEET / JEE / AIIMS / CUET) may appear on the Q header line.
    """
    return await _do_ingest_pyqs(pg, book_id, chapter_id, body)


# ── PYQs — file upload ───────────────────────────────────────────────

@router.post(
    "/books/{book_id}/chapters/{chapter_id}/pyqs/file",
    response_model=PYQIngestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest PYQ blocks (plain-text file upload)",
)
async def ingest_pyqs_file(
    book_id: uuid.UUID,
    chapter_id: uuid.UUID,
    pg: PgDep,
    _admin: AdminDep,
    file: UploadFile = File(..., description="Plain .txt file with PYQ blocks"),
) -> PYQIngestOut:
    """
    Same as the raw-text endpoint, but accepts a plain-text **file upload**
    instead of form body.  Useful for bulk imports.
    """
    raw = (await file.read()).decode("utf-8", errors="replace")
    return await _do_ingest_pyqs(pg, book_id, chapter_id, raw)


# ── Shared ingestion logic ────────────────────────────────────────────

async def _do_ingest_pyqs(
    pg: "PostgresHandler",
    book_id: uuid.UUID,
    chapter_id: uuid.UUID,
    raw: str,
) -> PYQIngestOut:
    """Parse blocks and store them; return counts."""
    from Core.Storage.PostgresHandler import PostgresHandler

    # Validate chapter belongs to book
    pool = pg._pool_guard()
    chapter_row = await pool.fetchrow(
        "SELECT chapter_id FROM core.chapters WHERE chapter_id = $1 AND book_id = $2",
        chapter_id, book_id,
    )
    if not chapter_row:
        raise HTTPException(
            status_code=404,
            detail=f"Chapter {chapter_id} not found under book {book_id}.",
        )

    blocks = parse_pyq_blocks(raw)
    if not blocks:
        raise HTTPException(
            status_code=422,
            detail="No valid PYQ blocks found. Check the block format.",
        )

    inserted = 0
    skipped  = 0
    pyq_ids: List[uuid.UUID] = []

    for blk in blocks:
        try:
            rec = await pg.create_pyq(
                chapter_id=chapter_id,
                question=blk.question,
                answer=blk.answer,
                year=blk.year,
                exam=blk.exam,
                marks=blk.marks,
            )
            pyq_ids.append(rec["pyq_id"])
            inserted += 1
        except Exception as exc:
            logger.warning("PYQ insert failed: %s", exc)
            skipped += 1

    return PYQIngestOut(inserted=inserted, skipped=skipped, pyq_ids=pyq_ids)
