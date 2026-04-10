"""RAG chat script – hybrid retrieval + query expansion.

Connects to pgvector + PostgreSQL, finds the most relevant nodes for a
hardcoded question from lebo101.pdf using hybrid search (vector + keyword),
then asks Gemini to compose a structured answer with diagram URLs.
"""

import asyncio
import logging
import os
import textwrap

from dotenv import load_dotenv
from google import genai

from Core.Embedder import Embedder
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler
from Core.Storage.VectorHandler import VectorHandler

# ─── logging ────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ─── Hardcoded question (from lebo101.pdf – The Living World) ───────
QUESTION = "Who was Panchanan Maheshwari and what field did he contribute to?"


# ─── Gemini wrappers ────────────────────────────────────────────────

class GeminiLLM:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        return response.text


class GeminiEmbedModel:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Embed each text individually — Gemini's embed_content treats a
        # list of strings as parts of ONE content (returning 1 embedding),
        # not as separate items.
        results: list[list[float]] = []
        for text in texts:
            response = await self.client.aio.models.embed_content(
                model="gemini-embedding-2-preview",
                contents=text,
            )
            results.append(response.embeddings[0].values)
        return results


# ─── helpers ────────────────────────────────────────────────────────

def build_context_block(nodes):
    """Build a numbered context string from retrieved nodes."""
    parts = []
    for i, node in enumerate(nodes, 1):
        content = node.get("content", "")
        image_url = node.get("image_url")
        rrf = node.get("rrf_score", 0.0)
        vec = node.get("similarity_score", 0.0)

        block = f"--- Context {i}  (rrf={rrf:.4f}  vec={vec:.4f}) ---\n{content}"
        if image_url:
            block += f"\n[Diagram: {image_url}]"
        parts.append(block)
    return "\n\n".join(parts)


def build_prompt(question: str, context: str) -> str:
    return textwrap.dedent(f"""\
        You are an expert NCERT Biology tutor.  Answer the student's question
        using ONLY the context provided below.  Follow these rules:

        1. Give a clear, structured answer with headings and bullet points.
        2. Where a diagram URL appears in the context (e.g. [Diagram: https://...]),
           reference it in your answer as:
           📊 See diagram: <url>
        3. If the context does not contain enough information, say so honestly.
        4. Do NOT invent facts.

        ── CONTEXT ──
        {context}

        ── QUESTION ──
        {question}

        ── ANSWER ──
    """)


# ─── main ───────────────────────────────────────────────────────────

async def main():
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.error("GEMINI_API_KEY not set in environment.")
        return

    llm = GeminiLLM(api_key)
    embed_model = GeminiEmbedModel(api_key)

    pg = PostgresHandler()
    vec = VectorHandler()
    bucket = BucketHandler()

    try:
        await pg.connect()
        await vec.connect()
        logger.info("Connected to databases.")
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return

    embedder = Embedder(
        pg=pg, vec=vec, bucket=bucket,
        llm_client=llm, embed_model=embed_model,
    )

    try:
        # ── 1. Find the chapter ──────────────────────────────────────
        pool = pg._pool_guard()
        row = await pool.fetchrow(
            "SELECT id FROM core.chapters ORDER BY created_at DESC LIMIT 1"
        )
        if not row:
            logger.error("No chapters found. Run test.py first.")
            return
        chapter_id = str(row["id"])
        logger.info(f"Using chapter: {chapter_id}")

        # ── 2. Hybrid retrieve ──────────────────────────────────────
        logger.info(f"Question: {QUESTION}")

        TOP_K = 12
        nodes = await embedder.retrieve(QUESTION, chapter_id, limit=TOP_K)

        # Filter out diagram-only placeholder nodes (no useful text)
        nodes = [n for n in nodes if not (
            n.get("content", "").strip().startswith("Diagram ")
            and len(n.get("content", "").strip()) < 20
        )]

        if not nodes:
            logger.warning("No relevant nodes found.")
            return

        logger.info(f"Retrieved {len(nodes)} relevant nodes.")

        # ── 3. Build context & prompt ───────────────────────────────
        context = build_context_block(nodes)
        prompt = build_prompt(QUESTION, context)

        # ── 4. Ask Gemini ───────────────────────────────────────────
        logger.info("Generating answer via Gemini...")
        answer = await llm.generate(prompt)

        # ── 5. Print ────────────────────────────────────────────────
        print("\n" + "=" * 72)
        print(f"  QUESTION: {QUESTION}")
        print("=" * 72)
        print()
        print(answer)
        print()
        print("=" * 72)
        print("  RETRIEVED NODES (hybrid: vector + keyword, RRF ranked)")
        print("=" * 72)
        for i, node in enumerate(nodes, 1):
            rrf = node.get("rrf_score", 0)
            vec_s = node.get("similarity_score", 0)
            img = node.get("image_url")
            snippet = (node.get("content") or "")[:120].replace("\n", " ")
            line = f"  {i}. [rrf={rrf:.4f} vec={vec_s:.4f}] {snippet}..."
            if img:
                line += f"\n     📊 Image: {img}"
            print(line)
        print()

    finally:
        await pg.disconnect()
        await vec.disconnect()
        logger.info("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
