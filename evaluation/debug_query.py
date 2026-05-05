import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "Server"
sys.path.insert(0, str(SERVER_ROOT))

from Core.Parser.embedder import ChunkEmbedder
from Core.SRS.retriever import Retriever
from Core.Storage.PostgresHandler import PostgresHandler
from evaluation.retrieval_wrapper import ImprovedRetriever

async def main():
    os.environ["POSTGRES_USER"] = "preppanda"
    os.environ["POSTGRES_PASSWORD"] = "preppass"
    os.environ["POSTGRES_DB"] = "appdb"
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5432"

    questions = [
        "What is spermatogenesis?",
        "What is double fertilisation?",
        "What is DNA structure?",
        "What is reproductive health?",
    ]

    chapter_map = {
        "Human Reproduction": "e9b3f002-f293-40fe-8591-87f6dc44da5d",
        "Sexual Reproduction in Flowering Plants": "4450becc-0d5f-4587-9a16-7a17e1b111d8",
        "Molecular Basis of Inheritance": "1e04530f-c596-49a3-85e3-b44bc655daed",
        "Reproductive Health": "7ba50bb0-0e79-43dd-9525-b5fae00149d9",
    }

    pg = PostgresHandler()
    await pg.connect()
    try:
        embedder = ChunkEmbedder()
        base = Retriever(pg=pg, embedder=embedder)
        imp = ImprovedRetriever(pg=pg, embedder=embedder)

        for q in questions:
            print("QUESTION:", q)
            chapter_id = chapter_map.get("Human Reproduction") if "reproductive" in q.lower() else chapter_map.get("Human Reproduction")
            if "double fertilisation" in q.lower() or "pollination" in q.lower() or "apomixis" in q.lower():
                chapter_id = chapter_map.get("Sexual Reproduction in Flowering Plants")
            if "dna" in q.lower() or "genetic code" in q.lower() or "transcription" in q.lower():
                chapter_id = chapter_map.get("Molecular Basis of Inheritance")
            if "reproductive health" in q.lower() or "family planning" in q.lower():
                chapter_id = chapter_map.get("Reproductive Health")
            print("chapter_id", chapter_id)
            r = await base.retrieve(q, chapter_id)
            print("BASELINE TOP 5")
            for i,c in enumerate(r.chunks[:5], 1):
                print(i, c['chunk_id'], c.get('content','').replace('\n',' ')[:200])
            print("IMPROVED TOP 5")
            ir = await imp.retrieve(q, chapter_id, semantic_weight=0.6, keyword_weight=0.4, rerank=True, use_context_filter=True)
            for i,c in enumerate(ir.chunks[:5], 1):
                print(i, c['chunk_id'], c.get('content','').replace('\n',' ')[:200])
            print('='*80)
    finally:
        await pg.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
