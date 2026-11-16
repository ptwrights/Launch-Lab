
import json
import re
from pathlib import Path

import ollama

from hybrid_retrieval import hybrid_search

BASE_DIR = Path(__file__).resolve().parent


# The ten provision-level categories in section 7001(bbb)
CATEGORIES = {
    "(1)(A)": "Government Identifiers",
    "(1)(B)": "Financial Accounts and Credentials",
    "(1)(C)": "Precise Geolocation",
    "(1)(D)": "Sensitive Personal Characteristics",
    "(1)(E)": "Private Communications",
    "(1)(F)": "Genetic Data",
    "(1)(G)": "Neural Data",
    "(2)": "Biometric Identification",
    "(3)": "Health and Sexual Information",
    "(4)": "Personal Information of Minors"
}


def normalize(text):
    return " ".join(str(text).lower().split())


def find_source(phrase, passages):
    """Find an exact supporting phrase in the retrieved text."""

    for passage in passages:
        if normalize(phrase) in normalize(passage["text"]):
            return passage

    return None


def analyze_ccpa():

    print("Searching CCPA with BM25 + FAISS...")

    query = (
        "7001 sensitive personal information means "
        "consumer social security driver's license passport "
        "financial account precise geolocation genetic neural "
        "biometric health"
    )

    retrieved = hybrid_search(
        query,
        top_k=20,
        regulation="CCPA"
    )

    with open(
        BASE_DIR / "ccpa_chunks.json",
        "r",
        encoding="utf-8"
    ) as file:
        all_chunks = json.load(file)

    # Find the beginning of section 7001(bbb)
    start_chunk = None

    for result in retrieved:
        text = normalize(result["text"])

        if (
            "sensitive personal information" in text
            and "means:" in text
            and "social security" in text
        ):
            start_chunk = result["chunk_id"]
            break

    if start_chunk is None:
        raise ValueError(
            "Could not locate CCPA section 7001(bbb)."
        )

    # Include neighboring chunks containing the definition
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
        "Retrieved CCPA chunks:",
        [p["chunk_id"] for p in passages]
    )

    context = "\n".join(
        f"[PDF Page {p['page']}]\n{p['text']}"
        for p in passages
    )

    print("Analyzing CCPA with Ollama...")

    response = ollama.chat(
        model="llama3.2:3b",
        format="json",
        options={
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 1800
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "You analyze California Consumer Privacy Act "
                    "regulations. Extract sensitive personal "
                    "information categories only from section "
                    "7001(bbb). Return one category per provision "
                    "(1)(A) through (1)(G), plus (2), (3), and (4). "
                    "Return a single JSON object with an entities "
                    "array. Each entity must have a name beginning "
                    "with its provision label and a source_text "
                    "containing an exact phrase from the supplied "
                    "document. Do not invent source text."
                )
            },
            {
                "role": "user",
                "content": (
                    "Extract all supported categories:\n" + context
                )
            }
        ]
    )

    try:
        ai_results = json.loads(
            response["message"]["content"]
        )
    except json.JSONDecodeError:
        raise ValueError(
            "Ollama did not return valid JSON."
        )

    verified = {}

    # Step 1: Verify Ollama's extracted categories
    for entity in ai_results.get("entities", []):

        if not isinstance(entity, dict):
            continue

        name = entity.get("name", "")
        source_text = entity.get("source_text", "")

        if not isinstance(name, str):
            continue

        if not isinstance(source_text, str):
            continue

        match = re.match(
            r"^(\(1\)\([A-G]\)|\([2-4]\))",
            name.strip()
        )

        if not match:
            continue

        code = match.group(1)

        if code not in CATEGORIES:
            continue

        passage = find_source(source_text, passages)

        if passage and source_text.strip():

            verified[code] = {
                "name": f"{code} {CATEGORIES[code]}",
                "source_text": source_text.strip(),
                "page": passage["page"],
                "chunk_id": passage["chunk_id"],
                "regulatory_reference": (
                    f"11 CCR § 7001(bbb){code}"
                )
            }

    # Step 2: Recover categories Ollama missed
    # These phrases come from section 7001(bbb).
    FALLBACK_PHRASES = {
        "(1)(A)": "A consumer’s social security",
        "(1)(B)": "A consumer’s account log-in",
        "(1)(C)": "A consumer’s precise geolocation",
        "(1)(D)": "A consumer’s racial or ethnic origin",
        "(1)(E)": "The contents of a consumer’s mail",
        "(1)(F)": "A consumer’s genetic data",
        "(1)(G)": "A consumer’s neural data",
        "(2)": "The processing of biometric information",
        "(3)": (
            "Personal information collected and analyzed "
            "concerning a consumer’s health"
        ),
        "(4)": (
            "Personal information of consumers that the "
            "business has actual knowledge"
        )
    }

    for code, phrase in FALLBACK_PHRASES.items():

        if code in verified:
            continue

        passage = find_source(phrase, passages)

        if passage:

            verified[code] = {
                "name": f"{code} {CATEGORIES[code]}",
                "source_text": phrase,
                "page": passage["page"],
                "chunk_id": passage["chunk_id"],
                "regulatory_reference": (
                    f"11 CCR § 7001(bbb){code}"
                )
            }

            print(
                "Recovered missing category:",
                code
            )

    # Keep categories in regulatory order
    entities = [
        verified[code]
        for code in CATEGORIES
        if code in verified
    ]

    output = {
        "regulation": "CCPA",
        "document": (
            "California Consumer Privacy Act Regulations"
        ),
        "method": "Hybrid RAG (BM25 + FAISS)",
        "entities": entities
    }

    with open(
        BASE_DIR / "ccpa_analysis_results.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(output, file, indent=4)

    return output


if __name__ == "__main__":

    results = analyze_ccpa()

    print("\nCCPA analysis saved!")
    print(
        "Verified categories:",
        len(results["entities"])
    )

    for entity in results["entities"]:
        print(
            "-",
            entity["name"],
            "| Page:",
            entity["page"]
        )
