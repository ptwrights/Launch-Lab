
from retrieval import search_bm25
from dense_retrieval import search_dense


def hybrid_search(query, top_k=3, regulation="HIPAA"):

    # Existing regulations and uploaded IDs
    # are both supported
    regulation = regulation.upper()

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

    # Combine FAISS rankings
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
        "What types of personal information "
        "are protected by this regulation?"
    )

    results = hybrid_search(
        question,
        top_k=5,
        regulation="CCPA"
    )

    for rank, result in enumerate(results, start=1):
        print("\nRank:", rank)
        print("Page:", result["page"])
        print("Text:", result["text"][:400])
        print("-" * 40)


