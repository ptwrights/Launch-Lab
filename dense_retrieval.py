
import json
from pathlib import Path
from functools import lru_cache

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from retrieval import get_chunk_path

# Load the embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")


@lru_cache(maxsize=16)
def load_dense_index(regulation):
    file_path = get_chunk_path(regulation)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Chunk file not found: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    if not chunks:
        raise ValueError("Document has no chunks.")

    texts = [chunk["text"] for chunk in chunks]

    print(f"Creating embeddings for {regulation}...")

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
    results = search_dense(
        "What personal information is protected?",
        top_k=5,
        regulation="CCPA"
    )

    for result in results:
        print(result["page"], result["text"][:200])



