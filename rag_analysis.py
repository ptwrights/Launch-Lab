
import json
import re
import ollama
from pathlib import Path

from hybrid_retrieval import hybrid_search

# Find the project folder
BASE_DIR = Path(__file__).resolve().parent


def analyze_hipaa_rag():

    print("Searching HIPAA with BM25 + FAISS...")

    # Step 1: Search for HIPAA Safe Harbor identifiers
    query = (
        "HIPAA 164.514(b)(2)(i) list of identifiers "
        "including names social security numbers "
        "medical record numbers"
    )

    retrieved = hybrid_search(query, top_k=10)

    # Step 2: Load HIPAA document chunks
    with open(
        BASE_DIR / "hipaa_chunks.json",
        "r",
        encoding="utf-8"
    ) as file:
        all_chunks = json.load(file)

    # Step 3: Find the beginning of the Safe Harbor list
    start_chunk = None

    for result in retrieved:

        text = " ".join(result["text"].lower().split())

        if (
            "(2)(i)" in text
            and "identifiers" in text
        ):
            start_chunk = result["chunk_id"]
            break

    if start_chunk is None:

        print(
            "Retrieved chunk IDs:",
            [result["chunk_id"] for result in retrieved]
        )

        raise ValueError(
            "Could not locate the HIPAA Safe Harbor section."
        )

    # Step 4: Expand the retrieved legal context
    passages = []

    for i in range(
        start_chunk,
        min(start_chunk + 3, len(all_chunks))
    ):

        passages.append({
            "chunk_id": i,
            "page": all_chunks[i]["page"],
            "text": all_chunks[i]["text"]
        })

    print(
        "Retrieved legal context from chunks:",
        [passage["chunk_id"] for passage in passages]
    )

    # Step 5: Prepare legal text for Ollama
    context = ""

    for passage in passages:

        context += (
            f"\n[Page {passage['page']}]\n"
            f"{passage['text']}\n"
        )

    print("Analyzing retrieved passages with Ollama...")

    # Step 6: Extract HIPAA identifiers
    response = ollama.chat(
        model="llama3.2:3b",
        format="json",
        options={
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 1000
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "You are analyzing the HIPAA Privacy Rule. "
                    "Extract the 18 Safe Harbor identifier categories "
                    "from section 164.514(b)(2)(i), labeled "
                    "(A) through (R). "
                    "Return one entity for each lettered category "
                    "that appears in the supplied text. "
                    "Do not split categories into examples. "
                    "For example, street address, city, county, "
                    "and ZIP code belong to category (B). "
                    "Birth dates, admission dates, and ages over 89 "
                    "belong to category (C). "
                    "Do not extract identifiers from other sections. "
                    "Return exactly ONE JSON object with ONE "
                    "'entities' key. "
                    "The 'entities' value must be a single array "
                    "containing all extracted categories. "
                    "Never repeat the 'entities' key. "
                    "Use this structure: "
                    '{"entities": ['
                    '{"name": "(A) Names", '
                    '"source_text": "Names"}, '
                    '{"name": "(D) Telephone numbers", '
                    '"source_text": "Telephone numbers"}'
                    ']}. '
                    "These are examples of the format, "
                    "not the complete answer. "
                    "Include every supported category from A through R. "
                    "Each name must begin with its category letter. "
                    "Copy source_text exactly from the legal text. "
                    "Do not invent information."
                )
            },
            {
                "role": "user",
                "content": (
                    "Analyze these retrieved legal passages:\n"
                    + context
                )
            }
        ]
    )

    # Step 7: Parse the Ollama response
    try:

        results = json.loads(
            response["message"]["content"]
        )

    except json.JSONDecodeError:

        raise ValueError(
            "Ollama did not return valid JSON."
        )

    # Step 8: Verify extracted entities
    verified_entities = []
    seen_categories = set()

    for entity in results.get("entities", []):

        name = entity.get("name", "")
        source_text = entity.get("source_text", "")

        if not isinstance(name, str):
            continue

        if not isinstance(source_text, str):
            continue

        # Find category letter, such as (A)
        match = re.match(
            r"^\(([A-R])\)",
            name.strip()
        )

        if not match:
            continue

        category_letter = match.group(1)

        # Skip duplicate categories
        if category_letter in seen_categories:
            continue

        # Normalize whitespace in the supporting text
        clean_source = " ".join(
            source_text.lower().split()
        )

        # Verify the source phrase against the PDF text
        for passage in passages:

            clean_passage = " ".join(
                passage["text"].lower().split()
            )

            if clean_source and clean_source in clean_passage:

                verified_entities.append({
                    "name": name,
                    "source_text": source_text,
                    "page": passage["page"],
                    "chunk_id": passage["chunk_id"]
                })

                seen_categories.add(category_letter)
                break

    # Step 9: Prepare final analysis
    output = {
        "regulation": "HIPAA",
        "method": "Hybrid RAG (BM25 + FAISS)",
        "entities": verified_entities
    }

    # Step 10: Save the results
    output_path = BASE_DIR / "rag_analysis_results.json"

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=4
        )

    return output


if __name__ == "__main__":

    results = analyze_hipaa_rag()

    print("\nRAG analysis saved!")

    print(
        "Verified entities:",
        len(results["entities"])
    )

    for entity in results["entities"]:

        print(
            "-",
            entity["name"],
            "| Page:",
            entity["page"]
        )


