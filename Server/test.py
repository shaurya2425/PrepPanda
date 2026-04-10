import asyncio
import logging
import os
import uuid

from dotenv import load_dotenv
from google import genai

from Core.Embedder import Embedder
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler
from Core.Storage.VectorHandler import VectorHandler

# Setup logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class GeminiLLM:
    """Wrapper to expose an async `generate()` method to the Embedder."""
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model='gemma-4-31b-it',
            contents=prompt,
        )
        return response.text


class GeminiEmbedModel:
    """Wrapper to expose an async `embed()` method to the Embedder."""
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.aio.models.embed_content(
            model='gemini-embedding-2-preview',
            contents=texts,
        )
        # Assumes response.embeddings has a `values` attribute for the float list
        return [emb.values for emb in response.embeddings]


async def main():
    # Load env vars from .env
    load_dotenv()

    # ── 1. Setup API Keys & Gemini Wrappers ─────────────────────────
    api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY")
    if api_key == "YOUR_API_KEY":
        logger.warning("No GEMINI_API_KEY set. This will fail if not injected properly.")

    llm = GeminiLLM(api_key=api_key)
    embed_model = GeminiEmbedModel(api_key=api_key)

    # ── 2. Instantiate Handlers ─────────────────────────────────────
    pg = PostgresHandler()
    vec = VectorHandler()
    bucket = BucketHandler()

    # NOTE: You need proper env vars for Postgres/Bucket connections.
    # e.g., DATABASE_URL, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME, etc.
    try:
        await pg.connect()
        await vec.connect()
        logger.info("Connected to databases.")
    except Exception as e:
        logger.error(f"Failed to connect to databases. Are env vars set? Error: {e}")
        return

    # ── 3. Initialise Embedder ──────────────────────────────────────
    embedder = Embedder(
        pg=pg,
        vec=vec,
        bucket=bucket,
        llm_client=llm,
        embed_model=embed_model,
    )

    # ── 4. Set up DB Chapter (Foreign Key constraint) ───────────────
    try:
        # We need a valid chapter in the DB to associate the nodes with
        chapter = await pg.create_chapter(
            title="Test Chapter: lebo101",
            subject="Testing",
            pdf_url="local://lebo101.pdf"
        )
        chapter_id = str(chapter["id"])
        logger.info(f"Created testing chapter in DB: {chapter_id}")
    except Exception as e:
        logger.warning(f"Could not create chapter (possibly core.chapters table missing or error): {e}")
        # We'll just generate a dummy ID to proceed, but if DB enforces FK, node insertion will fail
        chapter_id = str(uuid.uuid4())
        logger.info(f"Falling back to dummy chapter ID: {chapter_id}")

    # ── 5. Run the Pipeline ─────────────────────────────────────────
    pdf_path = "lebo101.pdf"
    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found at {pdf_path}")
        return

    logger.info(f"Starting Embedder pipeline for: {pdf_path}")
    logger.info("This will extract text, chunk it structurally, ask Gemini for types, and insert nodes & embeddings...")

    try:
        node_ids = await embedder.process_pdf(chapter_id, pdf_path)
        logger.info(f"Pipeline finished! Created & embedded {len(node_ids)} nodes.")
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")

    # ── 6. Cleanup ──────────────────────────────────────────────────
    await pg.disconnect()
    await vec.disconnect()
    logger.info("Disconnected from databases.")


if __name__ == "__main__":
    asyncio.run(main())
