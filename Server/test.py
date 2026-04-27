"""
Full ingestion pipeline test.

Parses lebo101.pdf through both parsers, uploads images to the bucket,
and populates the DB:

    core.books
    core.chapters
    core.chunks           ← text nodes from NodeParser
    core.images           ← figures from VisualParser
    core.chunk_image_links← joined by matching figure_id
"""

import asyncio
import logging
import os
import re
import uuid

from dotenv import load_dotenv

from Core.Parser.NodeParser import parse_pdf_text, TextChunk, ImageRef
from Core.Parser.VisualParser import parse_pdf_visual, ImageBlock
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler

# ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────────────────────────────


def _safe_slug(text: str, max_len: int = 40) -> str:
    """Slugify a string for use in filenames."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug[:max_len]


# ─────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────

async def run_pipeline(
    pdf_path: str,
    book_title: str,
    grade: int,
    subject: str,
    chapter_number: int,
    chapter_title: str,
) -> None:

    # ── 1. Validate PDF ─────────────────────────────────────────────
    if not os.path.exists(pdf_path):
        logger.error("PDF not found: %s", pdf_path)
        return

    # ── 2. Init handlers ─────────────────────────────────────────────
    try:
        bucket = BucketHandler()
    except Exception as e:
        logger.error("BucketHandler init failed: %s", e)
        return

    pg = PostgresHandler()
    try:
        await pg.connect()
        logger.info("Connected to PostgreSQL.")
    except Exception as e:
        logger.error("PostgreSQL connection failed: %s", e)
        return

    try:
        await _ingest(pg, bucket, pdf_path, book_title, grade, subject, chapter_number, chapter_title)
    finally:
        await pg.disconnect()
        logger.info("Disconnected from PostgreSQL.")


async def _ingest(
    pg: PostgresHandler,
    bucket: BucketHandler,
    pdf_path: str,
    book_title: str,
    grade: int,
    subject: str,
    chapter_number: int,
    chapter_title: str,
) -> None:

    # ── 3. Parse PDF ─────────────────────────────────────────────────
    logger.info("Running NodeParser (text + refs)…")
    text_chunks, image_refs = parse_pdf_text(pdf_path)
    logger.info("NodeParser: %d chunks, %d unique figure refs", len(text_chunks), len(image_refs))

    logger.info("Running VisualParser (images)…")
    visual_chunks = parse_pdf_visual(pdf_path)
    # Flatten all ImageBlock objects from visual chunks
    visual_images: list[ImageBlock] = []
    for vc in visual_chunks:
        visual_images.extend(vc.images)
    logger.info("VisualParser: %d figure images captured", len(visual_images))

    # ── 4. Book + Chapter ────────────────────────────────────────────
    book = await pg.create_book(title=book_title, grade=grade, subject=subject)
    book_id: uuid.UUID = book["book_id"]
    logger.info("Created book: %s  (id=%s)", book_title, book_id)

    chapter = await pg.create_chapter(
        book_id=book_id,
        chapter_number=chapter_number,
        title=chapter_title,
    )
    chapter_id: uuid.UUID = chapter["chapter_id"]
    logger.info("Created chapter: %s  (id=%s)", chapter_title, chapter_id)

    # ── 5. Upload images → core.images ──────────────────────────────
    # figure_id → DB image record
    image_records: dict[str, dict] = {}

    for img in visual_images:
        if not img.image_bytes or not img.figure_id:
            continue

        # Upload to bucket
        slug = _safe_slug(img.caption or img.figure_id)
        filename = f"chapters/{chapter_id}/fig_{img.figure_id}_{slug}.png"
        try:
            image_path = bucket.upload_bytes(img.image_bytes, filename, "image/png")
            logger.info("Uploaded Fig %s → %s", img.figure_id, image_path)
        except Exception as e:
            logger.error("Failed to upload Fig %s: %s", img.figure_id, e)
            continue

        # Insert into core.images
        try:
            rec = await pg.create_image(
                chapter_id=chapter_id,
                image_path=image_path,
                caption=img.caption,
                position_index=img.page,  # use page number as coarse position
            )
            image_records[img.figure_id] = rec
            logger.info("Stored image  Fig %s  (image_id=%s)", img.figure_id, rec["image_id"])
        except Exception as e:
            logger.error("DB insert failed for Fig %s: %s", img.figure_id, e)

    logger.info("Images stored: %d / %d", len(image_records), len(visual_images))

    # ── 6. Insert text chunks → core.chunks ─────────────────────────
    # Dummy zero-vector — real embeddings come from the Embedder pipeline.
    ZERO_VEC: list[float] = [0.0] * 768

    chunk_records: list[dict] = []

    for tc in text_chunks:
        try:
            rec = await pg.create_chunk(
                chapter_id=chapter_id,
                content=tc.content,
                token_count=tc.token_count,
                position_index=tc.position_index,
                embedding=ZERO_VEC,
                section_title=tc.section_title,
            )
            chunk_records.append({"db": rec, "tc": tc})
        except Exception as e:
            logger.warning(
                "Chunk insert failed (pos=%d, len=%d): %s",
                tc.position_index, len(tc.content), e,
            )

    logger.info("Chunks stored: %d / %d", len(chunk_records), len(text_chunks))

    # ── 7. Build chunk_image_links ───────────────────────────────────
    # For each chunk, look at figure_refs it contains and link to matching
    # image records.
    link_count = 0
    for entry in chunk_records:
        db_chunk = entry["db"]
        tc: TextChunk = entry["tc"]
        chunk_id: uuid.UUID = db_chunk["chunk_id"]

        for ref_id in tc.figure_refs:
            if ref_id not in image_records:
                logger.debug("Chunk ref '%s' has no matching image in DB, skipping", ref_id)
                continue
            img_rec = image_records[ref_id]
            try:
                await pg.link_chunk_image(
                    chunk_id=chunk_id,
                    image_id=img_rec["image_id"],
                )
                link_count += 1
                logger.debug("Linked chunk %s ↔ image Fig %s", chunk_id, ref_id)
            except Exception as e:
                logger.warning("Link failed chunk=%s, fig=%s: %s", chunk_id, ref_id, e)

    logger.info("chunk_image_links created: %d", link_count)

    # ── 8. Summary ───────────────────────────────────────────────────
    logger.info(
        "\n"
        "═══════════════════════════════════════\n"
        "  Pipeline complete\n"
        "  Book:     %s  (%s)\n"
        "  Chapter:  %s\n"
        "  Chunks:   %d\n"
        "  Images:   %d\n"
        "  Links:    %d\n"
        "═══════════════════════════════════════",
        book_title, book_id,
        chapter_title,
        len(chunk_records),
        len(image_records),
        link_count,
    )


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    load_dotenv()

    asyncio.run(run_pipeline(
        pdf_path="lebo101.pdf",
        book_title="Biology Part I – Class XI",
        grade=11,
        subject="biology",
        chapter_number=1,
        chapter_title="Sexual Reproduction in Flowering Plants",
    ))
