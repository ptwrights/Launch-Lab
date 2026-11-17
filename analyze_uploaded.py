
import json
import re
import sys
from pathlib import Path

import ollama

from hybrid_retrieval import hybrid_search


BASE_DIR = Path(__file__).resolve().parent
CHUNK_DIR = BASE_DIR / "data" / "chunks"
MODEL = "llama3.2:3b"

QUERIES = [
    "personal information sensitive personal information definitions",
    "protected health information individually identifiable health information",
    "social security numbers names addresses phone numbers email addresses",
    "medical records patient identifiers account numbers",
    "personal data collection disclosure privacy safeguards",
    "health information privacy security breach notification",
]

# These are not personal information categories.
EXCLUDED_TERMS = {
    "united states code",
    "usc title",
    "u s code",
    "federal register",
    "public law",
    "code of federal regulations",
    "regulation",
    "statute",
    "section",
    "subsection",
    "congress",
    "department",
    "secretary",
    "agency",
    "government",
    "effective date",
    "appropriation",
    "funding",
}

DETECTOR_ALIASES = {
    "social security number": [
    "social security number",
    "social security numbers",
    "social security account number",
    "social security account numbers",
    "ssn",
    ],
    "email address": [
        "email address",
        "email addresses",
        "electronic mail address",
    ],
    "telephone number": [
        "telephone number",
        "telephone numbers",
        "phone number",
        "phone numbers",
    ],
    "ip address": [
        "ip address",
        "ip addresses",
        "internet protocol address",
    ],
    "account number": [
        "account number",
        "account numbers",
    ],
    "names": [
    "names",
    "name",
    "full name",
    "full names",
    "personal names",
    "individual names",
    "patient names",
    ],
}


def normalize(text):
    return " ".join(
        re.findall(r"[a-z0-9]+", str(text).lower())
    )


def valid_document_id(document_id):
    return bool(re.fullmatch(r"[0-9a-f]{32}", document_id))


def load_detectors():
    with open(
        BASE_DIR / "detectors.json",
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)["detectors"]


def find_detector(category, detectors):
    name = normalize(category)

    for detector in detectors:
        normalized_detector = normalize(detector)

        aliases = DETECTOR_ALIASES.get(
            normalized_detector,
            [normalized_detector],
        )

        if name in [normalize(alias) for alias in aliases]:
            return detector

    return None


def is_excluded(name):
    normalized = normalize(name)

    if not normalized:
        return True

    for term in EXCLUDED_TERMS:
        if normalized == normalize(term):
            return True

    # Reject references to legal titles and sections.
    if re.search(
        r"\b(title|section|chapter)\s+\d+\b",
        normalized,
    ):
        return True

    return False


def collect_passages(document_id):
    passages = {}

    for query in QUERIES:
        results = hybrid_search(
            query,
            top_k=6,
            regulation=document_id,
        )

        for result in results:
            chunk_id = result["chunk_id"]

            if chunk_id not in passages:
                passages[chunk_id] = {
                    "chunk_id": chunk_id,
                    "page": result["page"],
                    "text": result["text"],
                }

    return list(passages.values())


def find_evidence(phrase, passages):
    normalized_phrase = normalize(phrase)

    if not normalized_phrase:
        return None

    for passage in passages:
        if normalized_phrase in normalize(passage["text"]):
            return passage

    return None


def validate_category(name, source_text):
    """Ask Ollama whether the entity is actually personal data."""

    response = ollama.chat(
        model=MODEL,
        format="json",
        options={
            "temperature": 0,
            "num_ctx": 2048,
            "num_predict": 150,
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "You classify extracted regulatory terms. "
                    "A valid category is a type of information "
                    "about an identifiable person, such as "
                    "medical records, email addresses, "
                    "biometric data, or financial account numbers. "
                    "Reject legal citations, laws, agencies, "
                    "document headings, procedures, funding, "
                    "and unrelated government terminology. "
                    "A reference to health information is valid "
                    "only when it describes information about "
                    "an individual. "
                    "Return JSON with exactly one boolean key "
                    "named 'valid'."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Category: {name}\n"
                    f"Supporting text: {source_text}"
                ),
            },
        ],
    )

    try:
        result = json.loads(response["message"]["content"])
        return result.get("valid") is True
    except (ValueError, TypeError, KeyError):
        return False


def analyze_uploaded(document_id):
    if not valid_document_id(document_id):
        raise ValueError("Invalid document ID.")

    chunk_path = CHUNK_DIR / f"{document_id}_chunks.json"

    if not chunk_path.exists():
        raise FileNotFoundError(
            "Uploaded document has not been chunked."
        )

    print("Searching uploaded regulation...")

    passages = collect_passages(document_id)

    if not passages:
        raise ValueError("No relevant passages found.")

    detectors = load_detectors()

    batches = [
        passages[i:i + 4]
        for i in range(0, len(passages), 4)
    ]

    verified = {}

    for batch_number, batch in enumerate(batches, 1):
        print(
            f"Analyzing batch {batch_number}/{len(batches)}..."
        )

        context = "\n\n".join(
            f"[Page {p['page']}, Chunk {p['chunk_id']}]\n"
            f"{p['text']}"
            for p in batch
        )

        response = ollama.chat(
            model=MODEL,
            format="json",
            options={
                "temperature": 0,
                "num_ctx": 4096,
                "num_predict": 1200,
            },
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract personal and sensitive "
                        "information categories from legal text. "
                        "Extract ONLY actual types of information "
                        "about identifiable individuals. "
                        "Examples include patient health records, "
                        "social security numbers, email addresses, "
                        "biometric identifiers, and financial "
                        "account numbers. "
                        "Do NOT extract laws, legal citations, "
                        "government agencies, statutes, titles, "
                        "sections, procedures, funding programs, "
                        "or general legal concepts. "
                        "Only include a category if the passage "
                        "explicitly supports it. "
                        "Return one JSON object containing an "
                        "'entities' array. Each entity must have "
                        "'name' and 'source_text'. "
                        "The source_text must be an exact phrase "
                        "copied from the supplied passage. "
                        "Do not invent information. "
                        "Example: "
                        '{"entities":[{"name":"Health Information",'
                        '"source_text":"individually identifiable '
                        'health information"}]}'
                    ),
                },
                {
                    "role": "user",
                    "content": context,
                },
            ],
        )

        try:
            ai_data = json.loads(
                response["message"]["content"]
            )
        except (ValueError, TypeError, KeyError):
            print("Skipping invalid AI response.")
            continue

        entities = ai_data.get("entities", [])

        if not isinstance(entities, list):
            continue

        for entity in entities:
            if not isinstance(entity, dict):
                continue

            name = entity.get("name", "")
            source_text = entity.get("source_text", "")

            if not isinstance(name, str):
                continue

            if not isinstance(source_text, str):
                continue

            name = name.strip()
            source_text = source_text.strip()

            if not name or not source_text:
                continue

            if is_excluded(name):
                continue

            evidence = find_evidence(source_text, batch)

            if evidence is None:
                continue

            key = normalize(name)

            if key in verified:
                continue

            print("Validating:", name)

            if not validate_category(name, source_text):
                print("Rejected:", name)
                continue

            verified[key] = {
                "name": name,
                "source_text": source_text,
                "page": evidence["page"],
                "chunk_id": evidence["chunk_id"],
            }

    results = []

    for entity in verified.values():
        detector = find_detector(
            entity["name"],
            detectors,
        )

        matched = detector is not None

        results.append({
            "regulation": document_id,
            "entity": entity["name"],
            "subcategories": [],
            "regulatory_reference": (
                f"Uploaded PDF page {entity['page']}"
            ),
            "detector": detector,
            "covered": matched,
            "status": (
                "Detector Match"
                if matched
                else "No Detector Match"
            ),
            "source_text": entity["source_text"],
            "page": entity["page"],
            "chunk_id": entity["chunk_id"],
        })

    output_path = (
        CHUNK_DIR / f"{document_id}_coverage.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(results, file, indent=4)

    print("\nAnalysis complete!")
    print("Verified categories:", len(results))
    print(
        "Detector matches:",
        sum(item["covered"] for item in results),
    )
    print("Saved to:", output_path)

    return results


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python analyze_uploaded.py "
            "<document_id>"
        )
        sys.exit(1)

    analyze_uploaded(sys.argv[1])

