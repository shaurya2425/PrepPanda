import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "Server"
sys.path.insert(0, str(SERVER_ROOT))

from Core.Parser.embedder import ChunkEmbedder
from Core.SRS.retriever import Retriever
from Core.Storage.PostgresHandler import PostgresHandler

QUESTIONS = [
    "What is spermatogenesis?",
    "Describe structure of testis",
    "What is fertilisation in humans?",
    "Explain implantation process",
    "What is role of placenta?",
    "What is double fertilisation?",
    "Explain types of pollination",
    "What is apomixis?",
    "Describe pre-fertilisation events",
    "What is DNA structure?",
    "What is genetic code?",
    "Explain transcription",
    "What is reproductive health?",
    "What are family planning methods?",
    "What are Mendel’s laws?",
]

DATASET_PATH = ROOT / "evaluation" / "dataset.json"


def load_environment() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(SERVER_ROOT / ".env")


CHAPTER_KEYWORDS = {
    "Human Reproduction": [
        "spermatogenesis",
        "testis",
        "fertilisation",
        "implantation",
        "placenta",
        "ovum",
        "zygote",
        "pregnancy",
    ],
    "Reproductive Health": [
        "reproductive health",
        "family planning",
        "contraception",
        "population",
        "infection",
        "STI",
    ],
    "Sexual Reproduction in Flowering Plants": [
        "double fertilisation",
        "pollination",
        "apomixis",
        "pre-fertilisation",
        "ovule",
        "pollen",
        "flower",
    ],
    "Reproduction in Organisms": [
        "fertilisation",
        "pollination",
        "vegetative",
        "sexual reproduction",
        "asexual reproduction",
    ],
    "Molecular Basis of Inheritance": [
        "dna structure",
        "genetic code",
        "transcription",
        "rna",
    ],
    "Principles of Inheritance and Variation": [
        "mendel",
        "law of segregation",
        "law of independent assortment",
        "law of dominance",
    ],
}


async def get_chapter_map(pg: PostgresHandler) -> dict[str, str]:
    pool = pg._pool_guard()
    rows = await pool.fetch(
        """
        SELECT c.chapter_id, c.title
        FROM core.chapters c
        JOIN core.books b ON c.book_id = b.book_id
        WHERE lower(b.subject) LIKE $1
          AND b.grade = 12
        """,
        "%biology%",
    )
    return {row["title"]: str(row["chapter_id"]) for row in rows}


def normalize_text(text: str) -> str:
    text_lower = text.strip().lower()
    text_lower = text_lower.rstrip("?.!")
    text_lower = re.sub(r"[^a-z0-9\s]", " ", text_lower)
    text_lower = re.sub(r"\s+", " ", text_lower).strip()
    return text_lower


def select_chapter_id(question: str, chapter_map: dict[str, str]) -> str:
    normalized_question = normalize_text(question)
    best_match = None
    best_score = (-1, -1)

    for title, keywords in CHAPTER_KEYWORDS.items():
        matched_keywords = [kw for kw in keywords if kw in normalized_question]
        if not matched_keywords:
            continue

        longest_match = max(len(kw) for kw in matched_keywords)
        match_count = len(matched_keywords)
        score = (longest_match, match_count)
        if score > best_score:
            best_match = title
            best_score = score

    if best_match is not None:
        if best_match in chapter_map:
            return chapter_map[best_match]

        for chapter_title, chapter_id in chapter_map.items():
            if best_match.lower() in chapter_title.lower():
                return chapter_id

    # fallback to first title match by keyword in chapter title
    for chapter_title, chapter_id in chapter_map.items():
        if any(keyword in chapter_title.lower() for keywords in CHAPTER_KEYWORDS.values() for keyword in keywords):
            return chapter_id

    # fallback to the first available chapter
    if chapter_map:
        return next(iter(chapter_map.values()))
    raise RuntimeError("No chapters available to select.")


async def build_dataset(output_path: str = None) -> None:
    load_environment()
    output_path = Path(output_path or DATASET_PATH)

    pg = PostgresHandler()
    await pg.connect()
    try:
        chapter_map = await get_chapter_map(pg)
        print(f"Found {len(chapter_map)} Biology chapter(s) for dataset creation.")

        embedder = ChunkEmbedder()
        retriever = Retriever(pg=pg, embedder=embedder)

        data = []
        for question in QUESTIONS:
            chapter_id = select_chapter_id(question, chapter_map)
            print(f"Question '{question}' → chapter_id={chapter_id}")
            result = await retriever.retrieve(question, chapter_id)
            chunks = []
            seen = set()
            for chunk in result.chunks[:5]:
                chunk_id = str(chunk["chunk_id"])
                if chunk_id in seen:
                    continue
                seen.add(chunk_id)
                chunks.append({
                    "id": chunk_id,
                    "text": chunk.get("content", ""),
                })
                if len(chunks) >= 5:
                    break

            data.append(
                {
                    "question": question,
                    "chapter_id": chapter_id,
                    "chunks": chunks,
                    "graded_relevance": [],
                }
            )

        payload = {
            "chapter_id": data[0]["chapter_id"] if data else None,
            "questions": data,
            "source": "baseline_retriever",
            "description": "Fixed questions evaluated against top-5 baseline chunks from PrepPanda retrieval.",
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Dataset written to {output_path}")
    finally:
        await pg.disconnect()


if __name__ == "__main__":
    asyncio.run(build_dataset())
