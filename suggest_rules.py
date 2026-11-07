
import json

# Read detector coverage results
with open("coverage_results.json", "r") as file:
    results = json.load(file)

# Example candidate rules for selected identifier categories
rule_templates = {
    "Medical Record Number": {
        "method": "Regex + validation",
        "pattern": r"\bMRN[-:\s]?\d{5,10}\b",
        "notes": "Example format only. Actual MRN formats vary."
    },
    "Health Plan Beneficiary Number": {
        "method": "Regex + validation",
        "pattern": r"\b[A-Z]{2}\d{8}\b",
        "notes": "Illustrative pattern; requires plan-specific validation."
    },
    "Certificate/License Number": {
        "method": "Dictionary + regex",
        "pattern": None,
        "notes": "Requires jurisdiction-specific formats."
    },
    "Biometric Identifiers": {
        "method": "Specialized biometric detection",
        "pattern": None,
        "notes": "Requires specialized processing beyond text regex."
    },
    "Full-Face Photographs": {
        "method": "Image recognition",
        "pattern": None,
        "notes": "Requires image-based detection."
    }
}

# Add suggestions to gaps
for item in results:
    if not item["covered"]:
        suggestion = rule_templates.get(item["entity"])

        if suggestion:
            item["suggested_rule"] = suggestion
        else:
            item["suggested_rule"] = {
                "method": "Manual review",
                "pattern": None,
                "notes": "No candidate rule available yet."
            }

# Save updated report
with open("coverage_results.json", "w") as file:
    json.dump(results, file, indent=4)

print("Candidate detection rules added!")

for item in results:
    if not item["covered"]:
        print(
            item["entity"],
            "->",
            item["suggested_rule"]["method"]
        )
