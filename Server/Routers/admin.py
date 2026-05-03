"""Admin router — protected data-ingestion endpoints.

Most routes require the ``X-Admin-Key`` header to match ``ADMIN_API_KEY``.
The `/admin/ingest-book` endpoint is intentionally open and does not require admin auth.

Endpoints
---------
POST /admin/books
    Create a new book entry.

POST /admin/books/{book_id}/chapters
    Upload a single chapter PDF and run the full ingestion pipeline.

POST /admin/ingest-book
    One-shot: create a book and ingest all its chapters in a single
    multipart request.  Chapter PDFs are matched to metadata via the
    ``chapters`` JSON field (ordered list of ``{number, title}``).

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

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from Core.Parser.chapter_pipeline import ChapterPipeline
from Routers.deps import AdminDep, BucketDep, EmbedDep, PgDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Max multipart part size — 200 MB (Starlette default is 1 MB).
_MAX_UPLOAD_BYTES = 200 * 1024 * 1024

# Max chapters processed concurrently during book ingestion.
# CPU-bound parsing runs in threads; this caps total parallelism.
_INGEST_CONCURRENCY = 4


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
    r"^---\s*Q\b(.*)?$",
    re.IGNORECASE,
)
_RE_ANS_HEADER = re.compile(r"^---Ans\b", re.IGNORECASE)
_RE_BLOCK_END  = re.compile(r"^---\s*$")
# Marks — matches both '5M' (legacy) and 'Marks 5' (new style)
_RE_MARKS      = re.compile(r"(?:Marks\s+(\d+)|\b(\d+)\s*[Mm]\b)", re.IGNORECASE)
# Year — matches both 'Year 2026' (new) and bare '2026' (legacy)
_RE_YEAR       = re.compile(r"(?:Year\s+(20\d{2}|19\d{2})|\b(20\d{2}|19\d{2})\b)", re.IGNORECASE)
_RE_EXAM       = re.compile(r"\b(CBSE|NEET|JEE|AIIMS|CUET)\b", re.IGNORECASE)


def _parse_q_header(header_rest: str) -> dict:
    """Extract marks, year, exam from the Q-header tail.

    Supports two formats:
    - Legacy: ``5M 2022``  or  ``NEET 3M 2023``
    - New:    ``Marks 5 Year 2022``  or  ``1 (OR) Marks 2 Year 2026``
    """
    meta: dict = {}
    m = _RE_MARKS.search(header_rest)
    if m:
        # group(1) = 'Marks N' style, group(2) = 'NM' style
        meta["marks"] = int(m.group(1) or m.group(2))
    m = _RE_YEAR.search(header_rest)
    if m:
        # group(1) = 'Year YYYY' style, group(2) = bare year
        meta["year"] = int(m.group(1) or m.group(2))
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

# ── Auth Verification ──────────────────────────────────────────────────
@router.get(
    "/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify admin credentials",
)
async def verify_admin(_admin: AdminDep):
    """Returns 200 OK if credentials are valid."""
    return {"status": "ok"}

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

@router.delete(
    "/books/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book",
)
async def delete_book(
    book_id: uuid.UUID,
    pg: PgDep,
    _admin: AdminDep,
):
    """Delete a book from core.books."""
    pool = pg._pool_guard()
    await pool.execute("DELETE FROM core.books WHERE book_id = $1", book_id)



# ── Ingest Book (one-shot) ────────────────────────────────────────────

class ChapterMeta(BaseModel):
    """Metadata for one chapter inside an ingest-book request."""
    number: int  = Field(..., ge=1, example=1)
    title:  str  = Field(..., example="Reproduction in Organisms")


class IngestBookChapterOut(BaseModel):
    chapter_number: int
    title:          str
    chapter_id:     uuid.UUID
    pdf_url:        Optional[str] = None
    chunk_count:    int
    image_count:    int
    link_count:     int
    embedded_count: int
    error:          Optional[str] = None   # set if this chapter failed


class IngestBookOut(BaseModel):
    book_id:        uuid.UUID
    title:          str
    grade:          int
    subject:        str
    chapters:       List[IngestBookChapterOut]
    total_chunks:   int
    total_images:   int
    failed_chapters: int


@router.post(
    "/ingest-book",
    response_model=IngestBookOut,
    status_code=status.HTTP_201_CREATED,
    summary="One-shot: create book + ingest all chapters",
)
async def ingest_book(
    request: Request,
    pg: PgDep,
    bucket: BucketDep,
    embedder: EmbedDep,
) -> IngestBookOut:
    """
    **One-shot book ingestion.**

    Two-phase architecture:

    1. **Receive** — read all PDFs into temp files (fast network I/O).
    2. **Process** — run the pipeline for every chapter concurrently
       (CPU-bound parsing in thread pool, async DB + S3 writes).

    A semaphore limits concurrency to avoid overwhelming the system
    (default: 4 chapters at a time).  A failure in one chapter is
    recorded but does **not** abort the remaining chapters.

    ### Request (multipart/form-data)
    | Field | Type | Description |
    |-------|------|-------------|
    | `title` | string | Book title |
    | `grade` | integer | Grade level (1–12) |
    | `subject` | string | Subject name |
    | `chapters` | JSON string | Ordered array of `{number, title}` objects |
    | `pdfs` | file[] | PDF files **in the same order** as `chapters` |

    ### Chapter matching
    `pdfs[0]` is ingested as `chapters[0]`, `pdfs[1]` as `chapters[1]`, etc.
    The arrays must be the same length.
    """
    import asyncio, json, tempfile, os

    # ── Parse multipart with raised size limit (200 MB per part) ─────
    form = await request.form(max_part_size=_MAX_UPLOAD_BYTES)

    title   = form.get("title")
    grade   = form.get("grade")
    subject = form.get("subject")
    chapters_raw = form.get("chapters")

    if not all([title, grade, subject, chapters_raw]):
        raise HTTPException(status_code=422, detail="Missing required fields: title, grade, subject, chapters")

    try:
        grade = int(grade)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="grade must be an integer")

    # Collect PDF files (form fields named "pdfs")
    pdfs: List[UploadFile] = [
        v for k, v in form.multi_items()
        if k == "pdfs" and hasattr(v, "read")
    ]

    # ── Parse chapters metadata ──────────────────────────────────────
    try:
        chapter_list = [ChapterMeta(**c) for c in json.loads(chapters_raw)]
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid chapters JSON: {exc}",
        )

    if len(chapter_list) != len(pdfs):
        raise HTTPException(
            status_code=422,
            detail=(
                f"chapters has {len(chapter_list)} entries but "
                f"{len(pdfs)} PDF files were uploaded. They must match."
            ),
        )

    # ─────────────────────────────────────────────────────────────────
    # PHASE 1 — Receive all PDFs → temp files  (fast, sequential I/O)
    # ─────────────────────────────────────────────────────────────────
    logger.info("Phase 1: receiving %d PDFs …", len(pdfs))

    prepared: List[dict] = []  # {meta, tmp_path, pdf_bytes}
    for meta, pdf_file in zip(chapter_list, pdfs):
        pdf_bytes = await pdf_file.read()
        suffix = os.path.splitext(pdf_file.filename or "chapter.pdf")[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        prepared.append({
            "meta": meta,
            "tmp_path": tmp_path,
            "pdf_bytes": pdf_bytes,
        })
        logger.info(
            "  ✓ Chapter %d (%s) — %.1f MB saved to %s",
            meta.number, meta.title,
            len(pdf_bytes) / (1024 * 1024), tmp_path,
        )

    await form.close()   # release multipart resources early

    # ── Create book ──────────────────────────────────────────────────
    book_rec = await pg.create_book(title=title, grade=grade, subject=subject)
    book_id: uuid.UUID = book_rec["book_id"]
    logger.info("Book created: '%s' (id=%s)", title, book_id)

    # ─────────────────────────────────────────────────────────────────
    # PHASE 2 — Process all chapters concurrently
    # ─────────────────────────────────────────────────────────────────
    pipeline = ChapterPipeline(pg=pg, bucket=bucket, embedder=embedder)
    sem = asyncio.Semaphore(_INGEST_CONCURRENCY)

    async def _process_one(item: dict) -> IngestBookChapterOut:
        meta     = item["meta"]
        tmp_path = item["tmp_path"]
        pdf_bytes = item["pdf_bytes"]

        async with sem:
            logger.info(
                "Phase 2: ingesting chapter %d — %s …",
                meta.number, meta.title,
            )
            try:
                result = await pipeline.ingest(
                    pdf_path=tmp_path,
                    book_id=book_id,
                    chapter_number=meta.number,
                    chapter_title=meta.title,
                    pdf_bytes=pdf_bytes,
                )
                return IngestBookChapterOut(
                    chapter_number=meta.number,
                    title=meta.title,
                    chapter_id=result.chapter_id,
                    pdf_url=result.pdf_url,
                    chunk_count=result.chunk_count,
                    image_count=result.image_count,
                    link_count=result.link_count,
                    embedded_count=result.embedded_count,
                )
            except Exception as exc:
                logger.exception(
                    "Chapter %d (%s) failed: %s",
                    meta.number, meta.title, exc,
                )
                return IngestBookChapterOut(
                    chapter_number=meta.number,
                    title=meta.title,
                    chapter_id=uuid.UUID(int=0),
                    chunk_count=0,
                    image_count=0,
                    link_count=0,
                    embedded_count=0,
                    error=str(exc),
                )
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # Fire all chapter tasks concurrently (capped by semaphore)
    chapter_results = await asyncio.gather(
        *[_process_one(item) for item in prepared]
    )

    # ── Aggregate ────────────────────────────────────────────────────
    total_chunks = sum(c.chunk_count for c in chapter_results)
    total_images = sum(c.image_count for c in chapter_results)
    failed       = sum(1 for c in chapter_results if c.error)

    logger.info(
        "Book ingestion complete: %d chapters, %d chunks, %d images, %d failed",
        len(chapter_list), total_chunks, total_images, failed,
    )

    return IngestBookOut(
        book_id=book_id,
        title=title,
        grade=grade,
        subject=subject,
        chapters=list(chapter_results),
        total_chunks=total_chunks,
        total_images=total_images,
        failed_chapters=failed,
    )



@router.post(
    "/books/{book_id}/chapters",
    response_model=ChapterOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & ingest a chapter PDF",
)
async def ingest_chapter(
    book_id: uuid.UUID,
    request: Request,
    pg: PgDep,
    bucket: BucketDep,
    embedder: EmbedDep,
    _admin: AdminDep,
) -> ChapterOut:
    """
    Upload a chapter PDF and run the full ingestion pipeline:

    - NodeParser (text chunks + figure refs)
    - VisualParser (figures → S3)
    - ChunkEmbedder (sentence-transformer embeddings)
    - Store everything in Postgres

    Returns counts for chunks, images, and chunk-image links.
    """
    import tempfile, os

    # Validate book exists
    pool = pg._pool_guard()
    book_row = await pool.fetchrow(
        "SELECT book_id FROM core.books WHERE book_id = $1", book_id
    )
    if not book_row:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found.")

    # ── Parse multipart with raised size limit ───────────────────────
    form = await request.form(max_part_size=_MAX_UPLOAD_BYTES)

    chapter_number = form.get("chapter_number")
    chapter_title  = form.get("chapter_title")
    pdf            = form.get("pdf")

    if not chapter_number or not chapter_title or not pdf:
        raise HTTPException(status_code=422, detail="Missing required fields: chapter_number, chapter_title, pdf")

    try:
        chapter_number = int(chapter_number)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="chapter_number must be an integer")

    if not hasattr(pdf, "read"):
        raise HTTPException(status_code=422, detail="pdf must be a file upload")

    # Save uploaded PDF to a temp path; also keep raw bytes for bucket upload
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

    await form.close()

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


# ── PYQs — raw body (book-level) ─────────────────────────────────────

@router.post(
    "/books/{book_id}/pyqs",
    response_model=PYQIngestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest PYQ blocks for a book (auto-maps to chapters)",
)
async def ingest_pyqs_text(
    book_id: uuid.UUID,
    pg: PgDep,
    embedder: EmbedDep,
    _admin: AdminDep,
    body: str = Form(
        ...,
        description=(
            "PYQ blocks in the block format:\n\n"
            "---Q Marks 5 Year 2022\n"
            "Question text\n"
            "---\n\n"
            "---Ans\n"
            "Answer text\n"
            "---"
        ),
    ),
) -> PYQIngestOut:
    """
    Ingest PYQ blocks for an entire book.

    Each question is automatically mapped to the most relevant chapter
    by comparing its embedding against all chunks in the book.  The top
    matching chunks are also linked in ``core.pyq_chunk_map``.

    Both header formats are supported:
    - New:    ``---Q 1 Marks 2 Year 2026``
    - Legacy: ``---Q 5M 2022``
    """
    return await _do_ingest_pyqs(pg, embedder, book_id, body)


# ── PYQs — file upload (book-level) ──────────────────────────────────

@router.post(
    "/books/{book_id}/pyqs/file",
    response_model=PYQIngestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest PYQ blocks from file (auto-maps to chapters)",
)
async def ingest_pyqs_file(
    book_id: uuid.UUID,
    pg: PgDep,
    embedder: EmbedDep,
    _admin: AdminDep,
    file: UploadFile = File(..., description="Plain .txt file with PYQ blocks"),
) -> PYQIngestOut:
    """
    Same as the raw-text endpoint, but accepts a plain-text **file upload**
    instead of form body.  Useful for bulk imports.
    """
    raw = (await file.read()).decode("utf-8", errors="replace")
    return await _do_ingest_pyqs(pg, embedder, book_id, raw)


# ── Shared PYQ ingestion + semantic mapping ───────────────────────────

# How many top chunks to link per PYQ via pyq_chunk_map.
_PYQ_TOP_K_CHUNKS = 5

async def _do_ingest_pyqs(
    pg: "PostgresHandler",
    embedder: "ChunkEmbedder",
    book_id: uuid.UUID,
    raw: str,
) -> PYQIngestOut:
    """Parse PYQ blocks, store them, and semantically map each to a chapter.

    Pipeline per question:
    1. Insert PYQ row (book_id set, chapter_id=NULL)
    2. Embed the question text
    3. Cosine-search across all chunks in the book
    4. Assign the chapter of the best-matching chunk → update PYQ row
    5. Link top-K chunks in ``core.pyq_chunk_map``
    """
    import asyncio

    # ── Validate book ────────────────────────────────────────────────
    pool = pg._pool_guard()
    book_row = await pool.fetchrow(
        "SELECT book_id FROM core.books WHERE book_id = $1", book_id
    )
    if not book_row:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found.")

    # ── Parse blocks ─────────────────────────────────────────────────
    blocks = parse_pyq_blocks(raw)
    if not blocks:
        raise HTTPException(
            status_code=422,
            detail="No valid PYQ blocks found. Check the block format.",
        )

    # ── Phase 1: Insert all PYQ rows (chapter_id = NULL) ─────────────
    inserted = 0
    skipped  = 0
    pyq_records: List[dict] = []   # {pyq_id, question, ...}

    for blk in blocks:
        try:
            rec = await pg.create_pyq(
                book_id=book_id,
                question=blk.question,
                answer=blk.answer,
                year=blk.year,
                exam=blk.exam,
                marks=blk.marks,
            )
            pyq_records.append(rec)
            inserted += 1
        except Exception as exc:
            logger.warning("PYQ insert failed: %s", exc)
            skipped += 1

    if not pyq_records:
        return PYQIngestOut(inserted=0, skipped=skipped, pyq_ids=[])

    # ── Phase 2: Semantic mapping (embed → match → assign) ───────────
    logger.info("PYQ mapping: embedding %d questions …", len(pyq_records))

    questions = [r["question"] for r in pyq_records]
    q_embeddings = await asyncio.to_thread(embedder.encode, questions)

    # Fetch all chunk embeddings for this book in one query
    chunk_rows = await pool.fetch(
        """
        SELECT c.chunk_id, c.chapter_id, c.embedding
        FROM core.chunks c
        JOIN core.chapters ch ON ch.chapter_id = c.chapter_id
        WHERE ch.book_id = $1
          AND c.embedding IS NOT NULL
        """,
        book_id,
    )

    if not chunk_rows:
        logger.warning(
            "No embedded chunks found for book %s — PYQs stored without chapter mapping.",
            book_id,
        )
        return PYQIngestOut(
            inserted=inserted,
            skipped=skipped,
            pyq_ids=[r["pyq_id"] for r in pyq_records],
        )

    # Build numpy arrays for fast cosine similarity
    import json as _json
    import numpy as np

    chunk_ids = [row["chunk_id"] for row in chunk_rows]
    chapter_ids = [row["chapter_id"] for row in chunk_rows]

    # pgvector returns embeddings as strings like "[0.1,0.2,...]"
    def _parse_embedding(emb):
        if isinstance(emb, str):
            return _json.loads(emb)
        return list(emb)

    chunk_matrix = np.array(
        [_parse_embedding(row["embedding"]) for row in chunk_rows],
        dtype=np.float32,
    )
    # Normalise chunk matrix (embeddings should already be normalised,
    # but guard against it)
    norms = np.linalg.norm(chunk_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    chunk_matrix /= norms

    mapped = 0
    linked = 0

    for rec, q_vec in zip(pyq_records, q_embeddings):
        pyq_id = rec["pyq_id"]

        # Cosine similarity = dot product (both normalised)
        q_arr = np.array(q_vec, dtype=np.float32)
        q_arr /= (np.linalg.norm(q_arr) or 1)
        scores = chunk_matrix @ q_arr

        # Top-K indices
        top_k = min(_PYQ_TOP_K_CHUNKS, len(scores))
        top_indices = np.argsort(scores)[-top_k:][::-1]

        # Best match → assign chapter
        best_idx = top_indices[0]
        best_chapter_id = chapter_ids[best_idx]
        best_score = float(scores[best_idx])

        try:
            await pg.update_pyq_chapter(pyq_id, best_chapter_id)
            mapped += 1
        except Exception as exc:
            logger.warning("PYQ chapter mapping failed for %s: %s", pyq_id, exc)

        # Link top-K chunks
        for idx in top_indices:
            try:
                await pg.link_pyq_chunk(
                    pyq_id=pyq_id,
                    chunk_id=chunk_ids[idx],
                    relevance=float(scores[idx]),
                )
                linked += 1
            except Exception as exc:
                logger.warning("PYQ-chunk link failed: %s", exc)

        logger.debug(
            "PYQ %s → chapter %s (score=%.3f, linked %d chunks)",
            pyq_id, best_chapter_id, best_score, top_k,
        )

    logger.info(
        "PYQ ingestion complete: %d inserted, %d skipped, %d mapped, %d chunk-links",
        inserted, skipped, mapped, linked,
    )

    return PYQIngestOut(
        inserted=inserted,
        skipped=skipped,
        pyq_ids=[r["pyq_id"] for r in pyq_records],
    )

@router.delete(
    "/pyqs/{pyq_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a PYQ",
)
async def delete_pyq(
    pyq_id: uuid.UUID,
    pg: PgDep,
    _admin: AdminDep,
):
    """Delete a PYQ from core.pyqs."""
    pool = pg._pool_guard()
    await pool.execute("DELETE FROM core.pyqs WHERE pyq_id = $1", pyq_id)

