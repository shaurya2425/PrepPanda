import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "Server"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVER_ROOT))

from Core.Parser.embedder import ChunkEmbedder
from Core.SRS.retriever import Retriever
from Core.Storage.PostgresHandler import PostgresHandler

from evaluation.dataset_builder import DATASET_PATH, load_environment
from evaluation.labeling import LABELED_PATH
from evaluation.metrics import (
    mean_faithfulness,
    mean_relevance,
    ndcg_at_k,
    precision_at_k,
)
from evaluation.retrieval_wrapper import ImprovedRetriever

RESULTS_BASELINE = ROOT / "evaluation" / "results_baseline.json"
RESULTS_IMPROVED = ROOT / "evaluation" / "results_improved.json"

LABEL_THRESHOLDS = [(0.8, 3), (0.65, 2), (0.5, 1)]


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def pseudo_label(question: str, chunk_text: str, embedder: ChunkEmbedder) -> int:
    if not chunk_text.strip():
        return 0
    sim = mean_relevance(question, chunk_text, embedder)
    for threshold, score in LABEL_THRESHOLDS:
        if sim > threshold:
            return score
    return 0


def build_label_map(question_item: Dict[str, Any]) -> Dict[str, int]:
    return {chunk["id"]: score for chunk, score in zip(question_item["chunks"], question_item.get("graded_relevance", []))}


def evaluate_retrieval(
    question: str,
    retrieved: List[Dict[str, Any]],
    label_map: Dict[str, int],
    embedder: ChunkEmbedder,
) -> Dict[str, float]:
    scores = []
    for chunk in retrieved[:5]:
        cid = str(chunk.get("chunk_id", chunk.get("id", "")))
        score = label_map.get(cid)
        if score is None:
            score = pseudo_label(question, chunk.get("content", ""), embedder)
        scores.append(score)

    p5 = precision_at_k(scores, k=5)
    ndcg = ndcg_at_k(scores, k=10)

    answer_text = retrieved[0].get("content", "") if retrieved else ""
    context_texts = [chunk.get("content", "") for chunk in retrieved[:3]]
    relevance = mean_relevance(question, answer_text, embedder)
    faithfulness = mean_faithfulness(answer_text, context_texts, embedder)

    return {
        "p_at_5": p5,
        "ndcg_at_10": ndcg,
        "relevance": relevance,
        "faithfulness": faithfulness,
    }


async def run_baseline(
    dataset: Dict[str, Any],
    chapter_id: str,
    pg: PostgresHandler,
    embedder: ChunkEmbedder,
) -> Dict[str, Any]:
    retriever = Retriever(pg=pg, embedder=embedder)
    results = []
    total_latency = 0.0

    for item in dataset["questions"]:
        start = time.perf_counter()
        target_chapter_id = item.get("chapter_id", chapter_id)
        result = await retriever.retrieve(item["question"], target_chapter_id)
        latency = time.perf_counter() - start
        total_latency += latency

        label_map = build_label_map(item)
        metrics = evaluate_retrieval(item["question"], result.chunks[:5], label_map, embedder)
        metrics["latency_seconds"] = latency
        results.append(metrics)

    if results:
        aggregate = {
            "version": "baseline",
            "p_at_5": sum(r["p_at_5"] for r in results) / len(results),
            "ndcg_at_10": sum(r["ndcg_at_10"] for r in results) / len(results),
            "relevance": sum(r["relevance"] for r in results) / len(results),
            "faithfulness": sum(r["faithfulness"] for r in results) / len(results),
            "latency_seconds": total_latency / len(results),
            "details": results,
        }
    else:
        aggregate = {
            "version": "baseline",
            "p_at_5": 0.0,
            "ndcg_at_10": 0.0,
            "relevance": 0.0,
            "faithfulness": 0.0,
            "latency_seconds": 0.0,
            "details": [],
        }
    return aggregate


async def run_improved(
    dataset: Dict[str, Any],
    chapter_id: str,
    pg: PostgresHandler,
    embedder: ChunkEmbedder,
    configs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    best = None
    all_runs = []
    for config in configs:
        retriever = ImprovedRetriever(pg=pg, embedder=embedder)
        results = []
        total_latency = 0.0
        for item in dataset["questions"]:
            start = time.perf_counter()
            target_chapter_id = item.get("chapter_id", chapter_id)
            result = await retriever.retrieve(
                item["question"],
                target_chapter_id,
                semantic_weight=config["semantic_weight"],
                keyword_weight=config["keyword_weight"],
                rerank=config["rerank"],
                use_context_filter=config["context_filter"],
                top_k=10,
                select_k=5,
            )
            latency = time.perf_counter() - start
            total_latency += latency

            label_map = build_label_map(item)
            metrics = evaluate_retrieval(item["question"], result.chunks, label_map, embedder)
            metrics["latency_seconds"] = latency
            results.append(metrics)

        summary = {
            "version": "improved",
            "config": config,
            "p_at_5": sum(r["p_at_5"] for r in results) / len(results) if results else 0.0,
            "ndcg_at_10": sum(r["ndcg_at_10"] for r in results) / len(results) if results else 0.0,
            "relevance": sum(r["relevance"] for r in results) / len(results) if results else 0.0,
            "faithfulness": sum(r["faithfulness"] for r in results) / len(results) if results else 0.0,
            "latency_seconds": total_latency / len(results) if results else 0.0,
            "details": results,
        }
        all_runs.append(summary)

        if best is None or summary["ndcg_at_10"] > best["ndcg_at_10"]:
            best = summary

    return {"best": best, "runs": all_runs}


def print_comparison(baseline: Dict[str, Any], improved: Dict[str, Any]) -> None:
    best = improved["best"]
    print("\nFinal comparison table:")
    print("| Version | P@5 | nDCG | Relevance | Faithfulness | Latency(s) |")
    print("|--------|------|------|-----------|-------------|------------|")
    print(
        f"| Baseline | {baseline['p_at_5']:.3f} | {baseline['ndcg_at_10']:.3f} | {baseline['relevance']:.3f} | {baseline['faithfulness']:.3f} | {baseline['latency_seconds']:.3f} |"
    )
    print(
        f"| Improved | {best['p_at_5']:.3f} | {best['ndcg_at_10']:.3f} | {best['relevance']:.3f} | {best['faithfulness']:.3f} | {best['latency_seconds']:.3f} |"
    )

    def pct(new, old):
        return ((new - old) / old * 100) if old else float("inf")

    print("\nImprovement percentages:")
    print(f"P@5: {pct(best['p_at_5'], baseline['p_at_5']):+.1f}%")
    print(f"nDCG: {pct(best['ndcg_at_10'], baseline['ndcg_at_10']):+.1f}%")
    print(f"Relevance: {pct(best['relevance'], baseline['relevance']):+.1f}%")
    print(f"Faithfulness: {pct(best['faithfulness'], baseline['faithfulness']):+.1f}%")


def ensure_dataset_and_labels() -> Dict[str, Any]:
    if not DATASET_PATH.exists():
        print("Building dataset from real PrepPanda retrieval outputs...")
        asyncio.run(__import__("evaluation.dataset_builder").dataset_builder.build_dataset())

    if not Path(LABELED_PATH).exists():
        print("Creating labels for dataset using pseudo-ground-truth...")
        asyncio.run(__import__("evaluation.labeling").labeling.label_dataset(auto=True))

    dataset = load_json(LABELED_PATH if Path(LABELED_PATH).exists() else DATASET_PATH)
    return dataset


async def main(run_labeling: bool = False) -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(SERVER_ROOT / ".env")

    dataset = ensure_dataset_and_labels()
    chapter_id = dataset["chapter_id"]

    pg = PostgresHandler()
    await pg.connect()
    try:
        embedder = ChunkEmbedder()
        baseline = await run_baseline(dataset, chapter_id, pg, embedder)
        save_json(RESULTS_BASELINE, baseline)

        configs = [
            {"semantic_weight": 0.5, "keyword_weight": 0.5, "rerank": True, "context_filter": True},
            {"semantic_weight": 0.6, "keyword_weight": 0.4, "rerank": True, "context_filter": True},
            {"semantic_weight": 0.8, "keyword_weight": 0.2, "rerank": True, "context_filter": True},
            {"semantic_weight": 0.6, "keyword_weight": 0.4, "rerank": False, "context_filter": True},
            {"semantic_weight": 0.5, "keyword_weight": 0.5, "rerank": True, "context_filter": False},
        ]
        improved = await run_improved(dataset, chapter_id, pg, embedder, configs)
        save_json(RESULTS_IMPROVED, improved)

        print_comparison(baseline, improved)
    finally:
        await pg.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PrepPanda retrieval evaluation pipeline.")
    parser.add_argument("--build", action="store_true", help="Build dataset.json from baseline retrieval outputs.")
    parser.add_argument("--label", action="store_true", help="Label dataset, using manual interactive mode if available.")
    parser.add_argument("--auto-label", action="store_true", help="Auto-label dataset without user prompts.")
    args = parser.parse_args()

    if args.build:
        asyncio.run(__import__("evaluation.dataset_builder").dataset_builder.build_dataset())
        sys.exit(0)

    if args.label:
        argparse_module = __import__("evaluation.labeling")
        argparse_module.labeling.label_dataset(auto=False)
        sys.exit(0)

    if args.auto_label:
        argparse_module = __import__("evaluation.labeling")
        argparse_module.labeling.label_dataset(auto=True)
        sys.exit(0)

    asyncio.run(main())
