
import json
import re

# Load the existing coverage results
with open("coverage_results.json", "r") as file:
    results = json.load(file)

# Load HIPAA text chunks with PDF page numbers
with open("hipaa_chunks.json", "r") as file:
    chunks = json.load(file)

# Find the section listing the 18 HIPAA identifiers
# Match the exact regulation reference first
section_pattern = re.compile(
    r"164\.514\s*\(b\)\s*\(2\)\s*\(i\)",
    re.IGNORECASE
)

# Find a passage containing several distinctive identifiers
keywords = [
    "social security numbers",
    "medical record numbers",
    "health plan beneficiary numbers"
]

source_pages = []

for chunk in chunks:
    text = chunk["text"].lower()

    if any(keyword in text for keyword in keywords):
        source_pages.append(chunk)

# Find supporting passages for each identifier
for item in results:
    letter = item["regulatory_reference"].split("(")[-1].replace(")", "")

    # Find the actual category heading in the text
    search_terms = [item["entity"]] + item.get("subcategories", [])

    matching_passages = []

    for chunk in source_pages:
        text = chunk["text"].lower()

        for term in search_terms:
            if term.lower() in text:
                matching_passages.append(chunk)
                break

    if matching_passages:
        first_match = matching_passages[0]

        item["page"] = first_match["page"]
        item["source_excerpt"] = first_match["text"][:400].strip()
    else:
        item["page"] = None
        item["source_excerpt"] = None

# Save updated results
with open("coverage_results.json", "w") as file:
    json.dump(results, file, indent=4)

print("Citation matching complete!")

for item in results:
    print(item["entity"], "-> Page", item["page"])
