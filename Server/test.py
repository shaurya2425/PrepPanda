"""
End-to-end pipeline test.

Runs ChapterPipeline (NodeParser + VisualParser + ChunkEmbedder)
on lebo101.pdf and populates the full DB schema.

    core.books
    core.chapters
    core.chunks           ← text + real embeddings (all-mpnet-base-v2)
    core.images           ← figures uploaded to bucket
    core.chunk_image_links← matched by figure_id
"""

import asyncio
import logging
import os
import uuid

from dotenv import load_dotenv

from Core.Parser.chapter_pipeline import ChapterPipeline
from Core.Parser.embedder import ChunkEmbedder
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler

# ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────────────────────────────

PDF_PATH      = "lebo101.pdf"
BOOK_TITLE    = "Biology Part I – Class XI"
GRADE         = 11
SUBJECT       = "biology"
CHAPTER_NUM   = 1
CHAPTER_TITLE = "Sexual Reproduction in Flowering Plants"


async def main() -> None:
    load_dotenv()

    # ── Validate PDF ─────────────────────────────────────────────────
    if not os.path.exists(PDF_PATH):
        logger.error("PDF not found: %s", PDF_PATH)
        return

    # ── Init handlers ─────────────────────────────────────────────────
    try:
        bucket = BucketHandler()
        logger.info("BucketHandler ready.")
    except Exception as e:
        logger.error("BucketHandler init failed: %s", e)
        return

    pg = PostgresHandler()
    try:
        await pg.connect()
        logger.info("PostgreSQL connected.")
    except Exception as e:
        logger.error("PostgreSQL connection failed: %s", e)
        return

    # Load embedding model once (downloads ~420 MB on first run)
    embedder = ChunkEmbedder()   # default: all-mpnet-base-v2, 768-dim

    try:
        # ── Create book ──────────────────────────────────────────────
        book = await pg.create_book(
            title=BOOK_TITLE,
            grade=GRADE,
            subject=SUBJECT,
        )
        book_id: uuid.UUID = book["book_id"]
        logger.info("Book created: %s  (id=%s)", BOOK_TITLE, book_id)

        # ── Run pipeline ─────────────────────────────────────────────
        pipeline = ChapterPipeline(pg=pg, bucket=bucket, embedder=embedder)
        result = await pipeline.ingest(
            pdf_path=PDF_PATH,
            book_id=book_id,
            chapter_number=CHAPTER_NUM,
            chapter_title=CHAPTER_TITLE,
        )

        # ── Final report ─────────────────────────────────────────────
        logger.info(
            "\n"
            "═══════════════════════════════════════\n"
            "  Test complete\n"
            "  Book:       %s\n"
            "  Chapter:    %s\n"
            "  Chunks:     %d  (embedded: %d)\n"
            "  Images:     %d\n"
            "  Links:      %d\n"
            "═══════════════════════════════════════",
            BOOK_TITLE,
            CHAPTER_TITLE,
            result.chunk_count,
            result.embedded_count,
            result.image_count,
            result.link_count,
        )

    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
    finally:
        await pg.disconnect()
        logger.info("Disconnected from PostgreSQL.")


if __name__ == "__main__":
    asyncio.run(main())
