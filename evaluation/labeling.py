import argparse
import json
import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "Server"
sys.path.insert(0, str(SERVER_ROOT))

DATASET_PATH = ROOT / "evaluation" / "dataset.json"
LABELED_PATH = ROOT / "evaluation" / "dataset_labeled.json"

STOPWORDS = set(
    [
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
        "explain",
        "describe",
        "define",
        "discuss",
        "name",
        "list",
        "give",
        "write",
        "mention",
        "state",
        "differentiate",
    ]
)


def load_environment() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(SERVER_ROOT / ".env")


def safe_parse_scores(raw: str, count: int) -> List[int]:
    tokens = raw.strip().replace(",", " ").split()
    if len(tokens) != count:
        raise ValueError(f"Expected {count} scores, got {len(tokens)}")
    scores = [int(t) for t in tokens]
    if any(s not in (0, 1, 2, 3) for s in scores):
        raise ValueError("Scores must be 0, 1, 2, or 3.")
    return scores


def cosine_similarity(vec1, vec2):
    import numpy as np

    vec1 = np.asarray(vec1, dtype=float)
    vec2 = np.asarray(vec2, dtype=float)
    denom = (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    return float(np.dot(vec1, vec2) / denom) if denom else 0.0


def auto_label_question(question: str, chunks: List[dict], model: SentenceTransformer) -> List[int]:
    texts = [question] + [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True)
    question_emb = embeddings[0]
    labels = []
    for chunk_emb in embeddings[1:]:
        sim = cosine_similarity(question_emb, chunk_emb)
        if sim > 0.8:
            labels.append(3)
        elif sim > 0.65:
            labels.append(2)
        elif sim > 0.5:
            labels.append(1)
        else:
            labels.append(0)
    return labels


def label_dataset(dataset_path: str = None, output_path: str = None, auto: bool = False) -> None:
    load_environment()
    dataset_path = Path(dataset_path or DATASET_PATH)
    output_path = Path(output_path or LABELED_PATH)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as f:
        dataset = json.load(f)

    model = SentenceTransformer("all-mpnet-base-v2")

    interactive = sys.stdin.isatty() and not auto
    for item in dataset.get("questions", []):
        if item.get("graded_relevance"):
            continue
        if interactive:
            print("\nQuestion:\n", item["question"])
            for idx, chunk in enumerate(item["chunks"], start=1):
                print(f"\n[{idx}] Chunk ID: {chunk['id']}")
                print(chunk["text"].strip())
            print("\nEnter 5 relevance scores for these chunks, separated by spaces.")
            print("Use 3=exact, 2=partial, 1=weak, 0=irrelevant. Type 'auto' to auto-label this question.")
            while True:
                raw = input("Scores: ").strip()
                if raw.lower() in ("auto", "a"):
                    item["graded_relevance"] = auto_label_question(
                        item["question"], item["chunks"], model
                    )
                    break
                try:
                    item["graded_relevance"] = safe_parse_scores(raw, len(item["chunks"]))
                    break
                except Exception as exc:
                    print(f"Invalid input: {exc}")
        else:
            item["graded_relevance"] = auto_label_question(
                item["question"], item["chunks"], model
            )

    dataset["pseudo_ground_truth"] = not interactive or auto
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"Labeled dataset written to {output_path}")
    if dataset["pseudo_ground_truth"]:
        print("Dataset is marked as pseudo_ground_truth.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label dataset relevance scores.")
    parser.add_argument("--auto", action="store_true", help="Auto-label all questions using embedding similarity.")
    parser.add_argument("--dataset", type=str, default=str(DATASET_PATH), help="Input dataset.json path.")
    parser.add_argument("--output", type=str, default=str(LABELED_PATH), help="Output dataset_labeled.json path.")
    args = parser.parse_args()
    label_dataset(dataset_path=args.dataset, output_path=args.output, auto=args.auto)
