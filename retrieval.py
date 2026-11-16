
import json
import re
from pathlib import Path
from functools import lru_cache
from rank_bm25 import BM25Okapi

BASE_DIR = Path(__file__).resolve().parent

REGULATIONS = {
    "HIPAA": "hipaa_chunks.json",
    "CCPA": "ccpa_chunks.json"
}


def tokenize(text):
    return re.findall(r"\w+", text.lower())


@lru_cache(maxsize=2)
def load_bm25(regulation):
    regulation = regulation.upper()

    if regulation not in REGULATIONS:
        raise ValueError("Unsupported regulation: " + regulation)

    file_path = BASE_DIR / REGULATIONS[regulation]

    with open(file_path, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    tokenized_chunks = [
        tokenize(chunk["text"])
        for chunk in chunks
    ]

    bm25 = BM25Okapi(tokenized_chunks)

    return chunks, bm25


def search_bm25(query, top_k=3, regulation="HIPAA"):
    chunks, bm25 = load_bm25(regulation)

    query_words = tokenize(query)
    scores = bm25.get_scores(query_words)

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    results = []

    for index in top_indices:
        results.append({
            "chunk_id": index,
            "page": chunks[index]["page"],
            "text": chunks[index]["text"],
            "score": float(scores[index])
        })

    return results


if __name__ == "__main__":
    question = "What information counts as personal information?"

    results = search_bm25(
        question,
        top_k=5,
        regulation="CCPA"
    )

    for result in results:
        print("\nPage:", result["page"])
        print("Score:", round(result["score"], 2))
        print("Text:", result["text"][:400])

