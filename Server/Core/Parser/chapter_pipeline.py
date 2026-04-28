"""Chapter ingestion pipeline.

Orchestrates both parsers and storage handlers to fully ingest a
single PDF chapter into the database:

    NodeParser   → text chunks   → core.chunks
    VisualParser → figure images → core.images  (via BucketHandler)
    figure_refs  ↔ figure_id     → core.chunk_image_links

Usage
-----
::

    from Core.Parser.chapter_pipeline import ChapterPipeline

    pipeline = ChapterPipeline(pg=pg_handler, bucket=bucket_handler)
    result   = await pipeline.ingest(
        pdf_path="lebo101.pdf",
        book_id=book_id,
        chapter_number=1,
        chapter_title="Sexual Reproduction in Flowering Plants",
    )
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from Core.Parser.NodeParser import parse_pdf_text, TextChunk, ImageRef
from Core.Parser.VisualParser import parse_pdf_visual, ImageBlock
from Core.Parser.embedder import ChunkEmbedder
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler

logger = logging.getLogger(__name__)

# Placeholder embedding — real vectors come from the Embedder later.
_EMBED_DIM = 768
_ZERO_VEC: List[float] = [0.0] * _EMBED_DIM


# ─────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class IngestResult:
    """Summary returned after a successful chapter ingestion."""
    chapter_id: uuid.UUID
    chunk_count: int = 0
    image_count: int = 0
    link_count: int = 0
    embedded_count: int = 0
    pdf_url: Optional[str] = None        # S3 URL of the uploaded raw PDF
    # Detailed records for downstream use (e.g. embedding pass)
    chunk_records: List[Dict[str, Any]] = field(default_factory=list)
    image_records: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _safe_slug(text: str, max_len: int = 40) -> str:
    """Slugify a string for filenames."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug[:max_len]


# ─────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────

class ChapterPipeline:
    """Ingest a single chapter PDF into the full storage stack.

    Parameters
    ----------
    pg : PostgresHandler
        Must already be connected (``await pg.connect()``).
    bucket : BucketHandler
        Instantiated and ready to upload.
    embedding_dim : int
        Dimension for zero-vector placeholders (default 768).
    """

    def __init__(
        self,
        pg: PostgresHandler,
        bucket: BucketHandler,
        embedder: Optional[ChunkEmbedder] = None,
        embedding_dim: int = _EMBED_DIM,
    ) -> None:
        self._pg = pg
        self._bucket = bucket
        self._embedder = embedder
        self._zero_vec = [0.0] * embedding_dim

    # ─────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────

    async def ingest(
        self,
        pdf_path: str,
        book_id: uuid.UUID,
        chapter_number: int,
        chapter_title: str,
        pdf_bytes: Optional[bytes] = None,
    ) -> IngestResult:
        """Run the full parse → upload → store → link pipeline.

        Parameters
        ----------
        pdf_path : str
            Path to the chapter PDF file.
        book_id : uuid.UUID
            Parent book ID (must already exist in ``core.books``).
        chapter_number : int
            Chapter number within the book.
        chapter_title : str
            Human-readable chapter title.
        pdf_bytes : bytes, optional
            Raw PDF bytes.  When provided the file is uploaded to the
            bucket as ``chapters/<chapter_id>/raw.pdf`` and the URL is
            stored on the chapter row.

        Returns
        -------
        IngestResult
            Summary with counts and DB records for downstream use.
        """
        # ── 1. Create chapter row ───────────────────────────────────
        chapter = await self._pg.create_chapter(
            book_id=book_id,
            chapter_number=chapter_number,
            title=chapter_title,
        )
        chapter_id: uuid.UUID = chapter["chapter_id"]
        logger.info("Created chapter '%s' (id=%s)", chapter_title, chapter_id)

        result = IngestResult(chapter_id=chapter_id)

        # ── 1b. Upload raw PDF to bucket ────────────────────────────
        if pdf_bytes:
            try:
                pdf_key = f"chapters/{chapter_id}/raw.pdf"
                pdf_url = self._bucket.upload_bytes(
                    pdf_bytes, pdf_key, "application/pdf"
                )
                result.pdf_url = pdf_url
                await self._pg.update_chapter_pdf_url(chapter_id, pdf_url)
                logger.info("Raw PDF uploaded: %s", pdf_url)
            except Exception as exc:
                logger.warning("PDF upload failed (non-fatal): %s", exc)

        # ── 2. Parse text ───────────────────────────────────────────
        logger.info("NodeParser: parsing %s …", pdf_path)
        text_chunks, image_refs = parse_pdf_text(pdf_path)
        logger.info(
            "NodeParser: %d chunks, %d figure refs",
            len(text_chunks), len(image_refs),
        )

        # ── 3. Parse images ─────────────────────────────────────────
        logger.info("VisualParser: parsing %s …", pdf_path)
        visual_chunks = parse_pdf_visual(pdf_path)
        visual_images: List[ImageBlock] = []
        for vc in visual_chunks:
            visual_images.extend(vc.images)
        logger.info("VisualParser: %d figure images", len(visual_images))

        # ── 4. Upload & store images ────────────────────────────────
        result.image_records = await self._store_images(
            chapter_id, visual_images,
        )
        result.image_count = len(result.image_records)

        # ── 5. Store text chunks ────────────────────────────────────
        result.chunk_records = await self._store_chunks(
            chapter_id, text_chunks,
        )
        result.chunk_count = len(result.chunk_records)

        # ── 6. Link chunks ↔ images ────────────────────────────────
        result.link_count = await self._link_chunks_images(
            result.chunk_records, result.image_records,
        )

        # ── 7. Embed chunks ─────────────────────────────────────────
        if self._embedder is not None:
            result.embedded_count = await self._embedder.embed_chunks(
                self._pg, result.chunk_records,
            )
        else:
            logger.info("No embedder provided — chunks stored with zero vectors")

        # ── 8. Summary ─────────────────────────────────────────────
        logger.info(
            "\n"
            "═══════════════════════════════════════\n"
            "  Chapter ingestion complete\n"
            "  Chapter:    %s\n"
            "  Chunks:     %d\n"
            "  Embedded:   %d\n"
            "  Images:     %d\n"
            "  Links:      %d\n"
            "═══════════════════════════════════════",
            chapter_title,
            result.chunk_count,
            result.embedded_count,
            result.image_count,
            result.link_count,
        )
        return result

    # ─────────────────────────────────────────────────────────────────
    # Private steps
    # ─────────────────────────────────────────────────────────────────

    async def _store_images(
        self,
        chapter_id: uuid.UUID,
        images: List[ImageBlock],
    ) -> Dict[str, Dict[str, Any]]:
        """Upload images to bucket and insert into ``core.images``.

        Returns a dict keyed by ``figure_id`` → DB record.
        """
        records: Dict[str, Dict[str, Any]] = {}

        for img in images:
            if not img.image_bytes or not img.figure_id:
                continue

            slug = _safe_slug(img.caption or img.figure_id)
            filename = f"chapters/{chapter_id}/fig_{img.figure_id}_{slug}.png"

            # Upload to bucket
            try:
                image_path = self._bucket.upload_bytes(
                    img.image_bytes, filename, "image/png",
                )
            except Exception as e:
                logger.error("Upload failed for Fig %s: %s", img.figure_id, e)
                continue

            # Insert DB record
            try:
                rec = await self._pg.create_image(
                    chapter_id=chapter_id,
                    image_path=image_path,
                    caption=img.caption,
                    position_index=img.page,
                )
                records[img.figure_id] = rec
                logger.debug(
                    "Stored Fig %s  (image_id=%s)", img.figure_id, rec["image_id"],
                )
            except Exception as e:
                logger.error("DB insert failed for Fig %s: %s", img.figure_id, e)

        logger.info("Images stored: %d / %d", len(records), len(images))
        return records

    async def _store_chunks(
        self,
        chapter_id: uuid.UUID,
        text_chunks: List[TextChunk],
    ) -> List[Dict[str, Any]]:
        """Insert text chunks into ``core.chunks``.

        Returns list of dicts with ``db`` (DB record) and ``tc``
        (TextChunk) for downstream linking.
        """
        entries: List[Dict[str, Any]] = []

        for tc in text_chunks:
            try:
                rec = await self._pg.create_chunk(
                    chapter_id=chapter_id,
                    content=tc.content,
                    token_count=tc.token_count,
                    position_index=tc.position_index,
                    embedding=self._zero_vec,
                    section_title=tc.section_title,
                )
                entries.append({"db": rec, "tc": tc})
            except Exception as e:
                logger.warning(
                    "Chunk insert failed (pos=%d): %s",
                    tc.position_index, e,
                )

        logger.info("Chunks stored: %d / %d", len(entries), len(text_chunks))
        return entries

    async def _link_chunks_images(
        self,
        chunk_entries: List[Dict[str, Any]],
        image_records: Dict[str, Dict[str, Any]],
    ) -> int:
        """Create ``core.chunk_image_links`` rows.

        For each chunk, match its ``figure_refs`` against stored images.
        """
        count = 0

        for entry in chunk_entries:
            db_chunk = entry["db"]
            tc: TextChunk = entry["tc"]
            chunk_id: uuid.UUID = db_chunk["chunk_id"]

            for ref_id in tc.figure_refs:
                if ref_id not in image_records:
                    continue
                try:
                    await self._pg.link_chunk_image(
                        chunk_id=chunk_id,
                        image_id=image_records[ref_id]["image_id"],
                    )
                    count += 1
                except Exception as e:
                    logger.warning(
                        "Link failed chunk=%s fig=%s: %s",
                        chunk_id, ref_id, e,
                    )

        logger.info("chunk_image_links created: %d", count)
        return count
