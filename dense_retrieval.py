
import json
from pathlib import Path
from functools import lru_cache

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent

REGULATIONS = {
    "HIPAA": "hipaa_chunks.json",
    "CCPA": "ccpa_chunks.json"
}

# Load the model once
model = SentenceTransformer("all-MiniLM-L6-v2")


@lru_cache(maxsize=2)
def load_dense_index(regulation):
    regulation = regulation.upper()

    if regulation not in REGULATIONS:
        raise ValueError("Unsupported regulation: " + regulation)

    file_path = BASE_DIR / REGULATIONS[regulation]

    with open(file_path, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    texts = [chunk["text"] for chunk in chunks]

    print(f"Creating {regulation} embeddings...")

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32"
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    return chunks, index


def search_dense(query, top_k=3, regulation="HIPAA"):
    chunks, index = load_dense_index(regulation)

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32"
    )

    scores, indices = index.search(
        query_embedding,
        min(top_k, len(chunks))
    )

    results = []

    for score, i in zip(scores[0], indices[0]):
        if i == -1:
            continue

        results.append({
            "chunk_id": int(i),
            "page": chunks[int(i)]["page"],
            "text": chunks[int(i)]["text"],
            "score": float(score)
        })

    return results


if __name__ == "__main__":
    question = "What types of personal information are protected?"

    results = search_dense(
        question,
        top_k=5,
        regulation="CCPA"
    )

    for result in results:
        print("\nPage:", result["page"])
        print("Similarity:", round(result["score"], 3))
        print("Text:", result["text"][:400])


