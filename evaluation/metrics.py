import time
from typing import Iterable, List

import numpy as np


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    a = np.asarray(vec1, dtype=float)
    b = np.asarray(vec2, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def precision_at_k(relevances: Iterable[int], k: int = 5) -> float:
    relevances = list(relevances)[:k]
    if not relevances:
        return 0.0
    return sum(1 for r in relevances if r > 0) / float(k)


def dcg_at_k(relevances: List[int], k: int = 10) -> float:
    relevances = list(relevances)[:k]
    return sum((2 ** rel - 1) / np.log2(idx + 2) for idx, rel in enumerate(relevances))


def ndcg_at_k(relevances: Iterable[int], k: int = 10) -> float:
    relevances = list(relevances)[:k]
    ideal = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal, k)
    if idcg <= 0:
        return 0.0
    return dcg_at_k(relevances, k) / idcg


def embed_similarity(question_embedding: List[float], answer_embedding: List[float]) -> float:
    return cosine_similarity(question_embedding, answer_embedding)


def _embedder_encode(embedder, texts: List[str]) -> List[List[float]]:
    if hasattr(embedder, "_model"):
        return embedder._model.encode(texts, normalize_embeddings=True)
    return embedder.encode(texts, normalize_embeddings=True)


def mean_relevance(question: str, answer: str, embedder) -> float:
    if not question or not answer:
        return 0.0
    embeddings = _embedder_encode(embedder, [question, answer])
    return cosine_similarity(embeddings[0], embeddings[1])


def mean_faithfulness(answer: str, contexts: List[str], embedder) -> float:
    if not answer or not contexts:
        return 0.0
    answer_emb = _embedder_encode(embedder, [answer])[0]
    context_text = " \n ".join(contexts)
    context_emb = _embedder_encode(embedder, [context_text])[0]
    return cosine_similarity(answer_emb, context_emb)


def measure_latency(callable_obj, *args, **kwargs):
    start = time.perf_counter()
    result = callable_obj(*args, **kwargs)
    end = time.perf_counter()
    return result, end - start


def measure_async_latency(coro):
    start = time.perf_counter()
    result = coro
    # Caller should await this
    return result, start
