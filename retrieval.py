
import json
import re
from pathlib import Path
from functools import lru_cache

from rank_bm25 import BM25Okapi

BASE_DIR = Path(__file__).resolve().parent

REGULATIONS = {
    "HIPAA": BASE_DIR / "hipaa_chunks.json",
    "CCPA": BASE_DIR / "ccpa_chunks.json",
}


def get_chunk_path(regulation):
    regulation = regulation.upper()

    if regulation in REGULATIONS:
        return REGULATIONS[regulation]

    # Uploaded documents use 32-character hex IDs
    document_id = regulation.lower()

    if (
        len(document_id) == 32
        and all(c in "0123456789abcdef" for c in document_id)
    ):
        return (
            BASE_DIR
            / "data"
            / "chunks"
            / f"{document_id}_chunks.json"
        )

    raise ValueError("Unsupported regulation or document ID.")


def tokenize(text):
    return re.findall(r"\w+", text.lower())


@lru_cache(maxsize=16)
def load_bm25(regulation):
    file_path = get_chunk_path(regulation)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Chunk file not found: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    if not chunks:
        raise ValueError("Document has no chunks.")

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
    results = search_bm25(
        "What information is protected?",
        top_k=5,
        regulation="CCPA"
    )

    for result in results:
        print(result["page"], result["text"][:200])


