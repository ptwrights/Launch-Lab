
import json
import re

# Load AI extraction results
with open("analysis_results.json", "r") as file:
    analysis = json.load(file)

# Load sample detector inventory
with open("detectors.json", "r") as file:
    detector_data = json.load(file)

# HIPAA Safe Harbor categories
categories = {
    "A": "Names",
    "B": "Geographic Subdivisions",
    "C": "Dates",
    "D": "Telephone Number",
    "E": "Fax Number",
    "F": "Email Address",
    "G": "Social Security Number",
    "H": "Medical Record Number",
    "I": "Health Plan Beneficiary Number",
    "J": "Account Number",
    "K": "Certificate/License Number",
    "L": "Vehicle Identifiers",
    "M": "Device Identifiers",
    "N": "Web URLs",
    "O": "IP Address",
    "P": "Biometric Identifiers",
    "Q": "Full-Face Photographs",
    "R": "Other Unique Identifiers"
}

# Alternate names used in the detector inventory
aliases = {
    "social security numbers": "Social Security Number",
    "electronic mail addresses": "Email Address",
    "telephone numbers": "Telephone Number",
    "internet protocol (ip) address numbers": "IP Address",
    "account numbers": "Account Number",
    "names": "Names"
}

def normalize(name):
    name = name.strip().lower()
    return aliases.get(name, name.title())

available_detectors = {
    normalize(name) for name in detector_data["detectors"]
}

# Group extracted entries by subsection
grouped = {}

for entity in analysis["entities"]:
    source = entity.get("source_text", "")
    match = re.fullmatch(r"\(([A-R])\)", source.strip())

    if not match:
        continue

    letter = match.group(1)

    if letter not in grouped:
        grouped[letter] = []

    grouped[letter].append(entity["name"])

# Compare categories against sample detectors
results = []

for letter, category in categories.items():

    # Only include categories found by the AI
    if letter not in grouped:
        continue

    normalized_category = normalize(category)
    covered = normalized_category in available_detectors

    results.append({
        "entity": category,
        "subcategories": grouped[letter],
        "regulatory_reference": (
            f"45 CFR 164.514(b)(2)(i)({letter})"
        ),
        "detector": category if covered else None,
        "covered": covered,
        "status": "Covered" if covered else "Gap",
        "source_text": None,
        "page": None
    })

# Save coverage report
with open("coverage_results.json", "w") as file:
    json.dump(results, file, indent=4)

# Display results
print("\nDetector Mapping Complete!\n")

for result in results:
    print(result["entity"], "->", result["status"])

covered_count = sum(item["covered"] for item in results)
gap_count = len(results) - covered_count

print("\nTotal HIPAA categories:", len(results))
print("Covered:", covered_count)
print("Gaps:", gap_count)

