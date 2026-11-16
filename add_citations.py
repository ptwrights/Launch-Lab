
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def normalize(text):
    return " ".join(str(text).lower().split())


# Load existing detector coverage
with open(
    BASE_DIR / "coverage_results.json",
    "r",
    encoding="utf-8"
) as file:
    results = json.load(file)


# Load HIPAA document chunks
with open(
    BASE_DIR / "hipaa_chunks.json",
    "r",
    encoding="utf-8"
) as file:
    chunks = json.load(file)


# Load verified RAG analysis, if available
rag_path = BASE_DIR / "rag_analysis_results.json"

rag_entities = {}

if rag_path.exists():

    with open(rag_path, "r", encoding="utf-8") as file:
        rag_data = json.load(file)

    for entity in rag_data.get("entities", []):

        match = re.match(
            r"^\(([A-R])\)",
            entity.get("name", "")
        )

        if match:
            rag_entities[match.group(1)] = entity


# Match citations to the exact source text
for item in results:

    reference = item.get("regulatory_reference", "")

    match = re.search(
        r"\(([A-R])\)$",
        reference
    )

    if not match:
        continue

    letter = match.group(1)

    # Prefer verified RAG evidence
    rag_entity = rag_entities.get(letter)

    if rag_entity:
        item["page"] = rag_entity.get(
            "page",
            item.get("page")
        )

        item["source_text"] = rag_entity.get(
            "source_text",
            item.get("source_text", "")
        )

    source_text = item.get("source_text", "").strip()

    if not source_text:
        continue

    # Search the original document for the exact phrase
    matching_chunk = None

    for chunk in chunks:

        if normalize(source_text) in normalize(chunk["text"]):
            matching_chunk = chunk
            break

    if matching_chunk:

        item["page"] = matching_chunk["page"]

        # Show the supporting phrase itself instead of
        # an unrelated 400-character excerpt.
        item["source_excerpt"] = source_text

    else:

        # Keep the verified source text and page number.
        # Do not erase citations when matching fails.
        item["source_excerpt"] = source_text


# Save updated report
with open(
    BASE_DIR / "coverage_results.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(results, file, indent=4)


print("\nHIPAA citation matching complete!")

for item in results:
    print(
        item["entity"],
        "-> Page",
        item.get("page")
    )

