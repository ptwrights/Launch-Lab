
from retrieval import search_bm25
from dense_retrieval import search_dense


def hybrid_search(query, top_k=3, regulation="HIPAA"):

    regulation = regulation.upper()

    # Search the selected regulation
    bm25_results = search_bm25(
        query,
        top_k=10,
        regulation=regulation
    )

    dense_results = search_dense(
        query,
        top_k=10,
        regulation=regulation
    )

    combined = {}
    k = 60

    # Combine BM25 rankings
    for rank, result in enumerate(bm25_results, start=1):

        chunk_id = result["chunk_id"]

        combined[chunk_id] = {
            "chunk_id": chunk_id,
            "page": result["page"],
            "text": result["text"],
            "score": 1 / (k + rank)
        }

    # Add FAISS rankings
    for rank, result in enumerate(dense_results, start=1):

        chunk_id = result["chunk_id"]

        if chunk_id in combined:
            combined[chunk_id]["score"] += 1 / (k + rank)

        else:
            combined[chunk_id] = {
                "chunk_id": chunk_id,
                "page": result["page"],
                "text": result["text"],
                "score": 1 / (k + rank)
            }

    ranked_results = sorted(
        combined.values(),
        key=lambda result: result["score"],
        reverse=True
    )

    return ranked_results[:top_k]


if __name__ == "__main__":

    question = (
        "What categories of personal information "
        "are defined under the California Consumer "
        "Privacy Act?"
    )

    results = hybrid_search(
        question,
        top_k=5,
        regulation="CCPA"
    )

    for rank, result in enumerate(results, start=1):

        print("\nRank:", rank)
        print("Chunk ID:", result["chunk_id"])
        print("Page:", result["page"])
        print("Text:", result["text"][:400])
        print("-" * 40)


