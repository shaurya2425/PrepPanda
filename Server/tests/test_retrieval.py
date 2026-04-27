"""
Retrieval and Generation test.

Tests the Smart Retrieval System (SRS):
1. Normalises and embeds a query
2. Retrieves chunks and images from the DB
3. Calls Gemini to generate an answer
4. Post-processes the markdown to include image URLs
"""

import asyncio
import logging
import os
import sys

# Add the parent directory to sys.path to allow importing from Core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

from Core.Parser.embedder import ChunkEmbedder
from Core.Storage.PostgresHandler import PostgresHandler
from Core.SRS import Retriever, Generator

# ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    load_dotenv()

    # ── Init handlers ─────────────────────────────────────────────────
    pg = PostgresHandler()
    try:
        await pg.connect()
        logger.info("PostgreSQL connected.")
    except Exception as e:
        logger.error("PostgreSQL connection failed: %s", e)
        return

    try:
        # ── 1. Fetch latest chapter ID ───────────────────────────────────
        # For testing, we'll just grab the most recently created chapter
        # If you have a specific chapter_id, you can hardcode it here
        pool = pg._pool_guard()
        row = await pool.fetchrow("SELECT chapter_id, title FROM core.chapters ORDER BY created_at DESC LIMIT 1")
        
        if not row:
            logger.error("No chapters found in the database. Please run test_parser.py first.")
            return
            
        chapter_id = row["chapter_id"]
        chapter_title = row["title"]
        logger.info(f"Using latest chapter: '{chapter_title}' (id={chapter_id})")

        # ── 2. Setup SRS ────────────────────────────────────────────────
        logger.info("Initializing Embedder...")
        embedder = ChunkEmbedder()
        
        logger.info("Initializing Retriever...")
        retriever = Retriever(pg=pg, embedder=embedder)
        
        logger.info("Initializing Generator...")
        generator = Generator() # Requires GEMINI_API_KEY in env

        # ── 3. Run Query ────────────────────────────────────────────────
        query = "Who was Panchanan Maheshwari, and what were his major contributions to botany and education?"
        
        logger.info(f"\n--- Running Query ---\nQuestion: {query}\n---------------------")
        
        result = await generator.answer(
            query=query,
            chapter_id=chapter_id,
            retriever=retriever,
        )

        # ── 4. Print Results ────────────────────────────────────────────
        print("\n\n" + "="*50)
        print("  SRS GENERATED ANSWER")
        print("="*50 + "\n")
        print(result.markdown)
        print("\n" + "="*50)
        
        logger.info(
            "Stats: Used %d chunks, %d images. Replaced %d image tags.",
            result.chunks_used,
            result.images_used,
            result.images_replaced
        )

    except Exception as e:
        logger.exception("Retrieval test failed: %s", e)
    finally:
        await pg.disconnect()
        logger.info("Disconnected from PostgreSQL.")


if __name__ == "__main__":
    asyncio.run(main())
