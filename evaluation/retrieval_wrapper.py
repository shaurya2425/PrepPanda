import asyncio
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "Server"
sys.path.insert(0, str(SERVER_ROOT))

from Core.Parser.embedder import ChunkEmbedder
from Core.Storage.PostgresHandler import PostgresHandler

STOPWORDS = {
    "what",
    "is",
    "are",
    "the",
    "a",
    "an",
    "of",
    "in",
    "and",
    "or",
    "how",
    "does",
    "do",
    "can",
    "which",
    "where",
    "when",
    "why",
    "that",
    "this",
    "these",
    "those",
    "for",
    "with",
    "by",
    "from",
    "on",
    "at",
    "into",
    "about",
    "explain",
    "describe",
    "define",
    "what",
    "tell",
    "show",
}

EXPANSION_MAP = {
    "difference": "diff",
    "explain": "describe",
}


def load_environment() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(SERVER_ROOT / ".env")


@dataclass
class RetrievalResult:
    query_normalized: str
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    context_chunks: List[Dict[str, Any]] = field(default_factory=list)


class ImprovedRetriever:
    def __init__(
        self,
        pg: PostgresHandler,
        embedder: ChunkEmbedder,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.5,
        pool_size: int = 30,
    ) -> None:
        self._pg = pg
        self._embedder = embedder
        self._semantic_weight = semantic_weight
        self._keyword_weight = keyword_weight
        self._pool_size = pool_size

    @staticmethod
    def normalize_query(query: str) -> str:
        query = query.strip().lower()
        query = query.rstrip("?.!")
        query = re.sub(r"[^a-z0-9\s]", " ", query)
        tokens = [EXPANSION_MAP.get(token, token) for token in query.split()]
        filtered = [token for token in tokens if token not in STOPWORDS]
        return " ".join(filtered) if filtered else " ".join(tokens)

    @staticmethod
    def _normalize_scores(scores: Dict[Any, float]) -> Dict[Any, float]:
        if not scores:
            return {}
        values = list(scores.values())
        min_val, max_val = min(values), max(values)
        if max_val - min_val == 0:
            return {k: 1.0 for k in scores}
        return {k: (v - min_val) / (max_val - min_val) for k, v in scores.items()}

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        import numpy as np

        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.dot(a, b) / denom) if denom else 0.0

    async def _rerank(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks:
            return []
        texts = [query] + [chunk.get("content", "") for chunk in chunks]
        embeddings = self._embedder.encode(texts)
        query_emb = embeddings[0]
        scores = [self._cosine(query_emb, emb) for emb in embeddings[1:]]
        for chunk, score in zip(chunks, scores):
            chunk["re_rank_score"] = score
        return sorted(chunks, key=lambda c: c["re_rank_score"], reverse=True)

    @staticmethod
    def _dedupe_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_ids = set()
        seen_texts = set()
        deduped = []
        for chunk in chunks:
            cid = str(chunk.get("chunk_id", ""))
            text = chunk.get("content", "").strip().lower()
            if cid in seen_ids or text in seen_texts:
                continue
            seen_ids.add(cid)
            seen_texts.add(text)
            deduped.append(chunk)
        return deduped

    async def retrieve(
        self,
        query: str,
        chapter_id: str,
        semantic_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
        rerank: bool = True,
        use_context_filter: bool = True,
        top_k: int = 10,
        select_k: int = 5,
    ) -> RetrievalResult:
        query_norm = self.normalize_query(query)
        query_emb = self._embedder.encode([query_norm])[0]

        semantic_hits = await self._pg.search_chunks_semantic(
            query_embedding=query_emb,
            chapter_id=chapter_id,
            limit=self._pool_size,
        )
        keyword_hits = await self._pg.search_chunks_keyword(
            query=query_norm,
            chapter_id=chapter_id,
            limit=self._pool_size,
        )

        sem_scores = {hit["chunk_id"]: hit.get("similarity_score", 0.0) for hit in semantic_hits}
        kwd_scores = {hit["chunk_id"]: hit.get("rank", 0.0) for hit in keyword_hits}
        chunk_map = {hit["chunk_id"]: hit for hit in semantic_hits + keyword_hits}

        norm_sem = self._normalize_scores(sem_scores)
        norm_kwd = self._normalize_scores(kwd_scores)

        semantic_weight = self._semantic_weight if semantic_weight is None else semantic_weight
        keyword_weight = self._keyword_weight if keyword_weight is None else keyword_weight

        scored = []
        for cid, chunk in chunk_map.items():
            s = norm_sem.get(cid, 0.0)
            k = norm_kwd.get(cid, 0.0)
            hybrid = semantic_weight * s + keyword_weight * k
            chunk["hybrid_score"] = hybrid
            scored.append((hybrid, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [chunk for _, chunk in scored[:top_k]]

        if rerank:
            top_chunks = await self._rerank(query_norm, top_chunks)

        top_chunks = self._dedupe_chunks(top_chunks)
        selected = top_chunks[:select_k]
        context_chunks = selected[:3] if use_context_filter else top_chunks[:3]

        return RetrievalResult(
            query_normalized=query_norm,
            chunks=selected,
            context_chunks=context_chunks,
        )


if __name__ == "__main__":
    load_environment()
    import argparse

    parser = argparse.ArgumentParser(description="Test improved retrieval wrapper")
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--chapter_id", type=str, required=True)
    parser.add_argument("--semantic_weight", type=float, default=0.5)
    parser.add_argument("--keyword_weight", type=float, default=0.5)
    parser.add_argument("--no_rerank", action="store_true")
    args = parser.parse_args()

    async def main() -> None:
        pg = PostgresHandler()
        await pg.connect()
        try:
            embedder = ChunkEmbedder()
            retriever = ImprovedRetriever(pg=pg, embedder=embedder)
            result = await retriever.retrieve(
                query=args.query,
                chapter_id=args.chapter_id,
                semantic_weight=args.semantic_weight,
                keyword_weight=args.keyword_weight,
                rerank=not args.no_rerank,
            )
            for idx, chunk in enumerate(result.chunks, start=1):
                print(f"[{idx}] {chunk.get('chunk_id')} score={chunk.get('hybrid_score')}")
                print(chunk.get('content', '')[:400])
                print("---")
        finally:
            await pg.disconnect()

    asyncio.run(main())
