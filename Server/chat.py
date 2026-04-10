"""RAG chat script – query existing embeddings and curate an answer.

Connects to pgvector, finds the most relevant nodes for a hardcoded
question from lebo101.pdf (NCERT Biology Ch. 1 – The Living World),
then asks Gemini to compose a structured answer, inlining diagram URLs
where images are attached to retrieved nodes.
"""

import asyncio
import logging
import os
import textwrap

from dotenv import load_dotenv
from google import genai

from Core.Storage.PostgresHandler import PostgresHandler
from Core.Storage.VectorHandler import VectorHandler

# ─── logging ────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ─── Hardcoded question (from lebo101.pdf – The Living World) ───────
QUESTION = "Who was Panchanan Maheshwari and what field did he contribute to?"


# ─── Gemini wrappers (same as test.py) ──────────────────────────────

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
        response = await self.client.aio.models.embed_content(
            model="gemini-embedding-2-preview",
            contents=texts,
        )
        return [emb.values for emb in response.embeddings]


# ─── helpers ────────────────────────────────────────────────────────

def build_context_block(nodes):
    """Build a numbered context string from retrieved nodes.

    If a node has an image_url, include it as a markdown image link so the
    LLM can reference the diagram in its answer.
    """
    parts = []
    for i, node in enumerate(nodes, 1):
        content = node.get("content", "")
        image_url = node.get("image_url")
        score = node.get("similarity_score", 0.0)

        block = f"--- Context {i}  (score: {score:.4f}) ---\n{content}"
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

    try:
        await pg.connect()
        await vec.connect()
        logger.info("Connected to databases.")
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return

    try:
        # ── 1. Find the chapter ──────────────────────────────────────
        pool = pg._pool_guard()
        row = await pool.fetchrow(
            "SELECT id FROM core.chapters ORDER BY created_at DESC LIMIT 1"
        )
        if not row:
            logger.error("No chapters found in the database. Run test.py first to ingest lebo101.pdf.")
            return
        chapter_id = row["id"]
        logger.info(f"Using chapter: {chapter_id}")

        # ── 2. Embed the question ───────────────────────────────────
        logger.info(f"Question: {QUESTION}")
        query_vec = (await embed_model.embed([QUESTION]))[0]

        # ── 3. Search pgvector for top-k similar nodes ──────────────
        TOP_K = 8
        results = await vec.search_similar(query_vec, chapter_id, limit=TOP_K)
        if not results:
            logger.warning("No similar nodes found. Is the chapter embedded?")
            return

        matched_ids = [r["node_id"] for r in results]
        nodes = await pg.get_nodes_by_ids(matched_ids)

        # Attach similarity scores
        score_map = {r["node_id"]: r["similarity_score"] for r in results}
        for node in nodes:
            node["similarity_score"] = score_map.get(node["id"], 0.0)
        nodes.sort(key=lambda n: n["similarity_score"], reverse=True)

        logger.info(f"Retrieved {len(nodes)} relevant nodes.")

        # ── 4. Build context & prompt ───────────────────────────────
        context = build_context_block(nodes)
        prompt = build_prompt(QUESTION, context)

        # ── 5. Ask Gemini ───────────────────────────────────────────
        logger.info("Generating answer via Gemini...")
        answer = await llm.generate(prompt)

        # ── 6. Print ────────────────────────────────────────────────
        print("\n" + "=" * 72)
        print(f"  QUESTION: {QUESTION}")
        print("=" * 72)
        print()
        print(answer)
        print()
        print("=" * 72)
        print("  RETRIEVED NODES")
        print("=" * 72)
        for i, node in enumerate(nodes, 1):
            score = node.get("similarity_score", 0)
            img = node.get("image_url")
            snippet = (node.get("content") or "")[:120].replace("\n", " ")
            line = f"  {i}. [score={score:.4f}] {snippet}..."
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
