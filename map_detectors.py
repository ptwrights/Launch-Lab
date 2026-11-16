
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# HIPAA Safe Harbor categories
HIPAA_CATEGORIES = {
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

# CCPA provision-level categories
CCPA_CATEGORIES = {
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

# Names used by the simulated detector inventory
ALIASES = {
    "social security numbers": "social security number",
    "electronic mail addresses": "email address",
    "telephone numbers": "telephone number",
    "internet protocol (ip) address numbers": "ip address",
    "account numbers": "account number",
    "names": "names"
}

# CCPA categories can be broader than individual detectors.
# These are potential detector matches, not legal compliance checks.
CCPA_DETECTOR_MATCHES = {
    "(1)(A)": ["social security number"],
    "(1)(B)": ["account number"],
    "(1)(C)": ["precise geolocation"],
    "(1)(D)": [],
    "(1)(E)": [],
    "(1)(F)": ["genetic data"],
    "(1)(G)": ["neural data"],
    "(2)": ["biometric identifiers"],
    "(3)": ["health information"],
    "(4)": []
}


def normalize(name):
    name = str(name).strip().lower()
    return ALIASES.get(name, name)


def load_detectors():
    with open(
        BASE_DIR / "detectors.json",
        "r",
        encoding="utf-8"
    ) as file:
        detector_data = json.load(file)

    return {
        normalize(name)
        for name in detector_data["detectors"]
    }


def map_hipaa(analysis, available_detectors):
    grouped = {}

    for entity in analysis.get("entities", []):
        name = entity.get("name", "")
        source = entity.get("source_text", "")

        match = re.match(r"^\(([A-R])\)", name.strip())

        if not match:
            match = re.fullmatch(
                r"\(([A-R])\)",
                source.strip()
            )

        if not match:
            continue

        letter = match.group(1)
        grouped.setdefault(letter, []).append(entity)

    results = []

    for letter, category in HIPAA_CATEGORIES.items():
        if letter not in grouped:
            continue

        entities = grouped[letter]
        first_entity = entities[0]

        covered = normalize(category) in available_detectors

        results.append({
            "regulation": "HIPAA",
            "entity": category,
            "subcategories": [
                item.get("name", "")
                for item in entities
            ],
            "regulatory_reference": (
                f"45 CFR 164.514(b)(2)(i)({letter})"
            ),
            "detector": category if covered else None,
            "covered": covered,
            "status": "Covered" if covered else "Gap",
            "source_text": first_entity.get("source_text", ""),
            "page": first_entity.get("page")
        })

    return results


def map_ccpa(analysis, available_detectors):
    grouped = {}

    for entity in analysis.get("entities", []):
        name = entity.get("name", "")

        match = re.match(
            r"^(\(1\)\([A-G]\)|\([2-4]\))",
            name.strip()
        )

        if not match:
            continue

        category_code = match.group(1)
        grouped.setdefault(category_code, []).append(entity)

    results = []

    for code, category in CCPA_CATEGORIES.items():
        if code not in grouped:
            continue

        entities = grouped[code]
        first_entity = entities[0]

        candidates = CCPA_DETECTOR_MATCHES.get(code, [])

        matched_detectors = [
            detector
            for detector in candidates
            if normalize(detector) in available_detectors
        ]

        # A match indicates partial detector capability,
        # not full coverage of a broad CCPA provision.
        if matched_detectors:
            status = "Partial Detector Match"
        else:
            status = "No Detector Match"

        results.append({
            "regulation": "CCPA",
            "entity": category,
            "subcategories": [
                item.get("name", "")
                for item in entities
            ],
            "regulatory_reference": (
                f"11 CCR 7001(bbb){code}"
            ),
            "detector": (
                ", ".join(matched_detectors)
                if matched_detectors else None
            ),
            "covered": False,
            "status": status,
            "source_text": first_entity.get("source_text", ""),
            "page": first_entity.get("page")
        })

    return results


def map_detectors(analysis=None, regulation="HIPAA"):
    regulation = regulation.upper()

    if regulation not in ("HIPAA", "CCPA"):
        raise ValueError("Unsupported regulation: " + regulation)

    if analysis is None:
        if regulation == "HIPAA":
            analysis_path = BASE_DIR / "analysis_results.json"
        else:
            analysis_path = BASE_DIR / "ccpa_analysis_results.json"

        with open(
            analysis_path,
            "r",
            encoding="utf-8"
        ) as file:
            analysis = json.load(file)

    available_detectors = load_detectors()

    if regulation == "HIPAA":
        results = map_hipaa(analysis, available_detectors)
        output_path = BASE_DIR / "coverage_results.json"
    else:
        results = map_ccpa(analysis, available_detectors)
        output_path = BASE_DIR / "ccpa_coverage_results.json"

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(results, file, indent=4)

    return results


if __name__ == "__main__":
    import sys

    regulation = (
        sys.argv[1].upper()
        if len(sys.argv) > 1
        else "HIPAA"
    )

    results = map_detectors(regulation=regulation)

    print(f"\n{regulation} Detector Mapping Complete!")

    for result in results:
        print(result["entity"], "->", result["status"])

    print("\nExtracted categories mapped:", len(results))

    if regulation == "HIPAA":
        covered = sum(item["covered"] for item in results)
        print("Covered:", covered)
        print("Potential gaps:", len(results) - covered)
    else:
        partial = sum(
            item["status"] == "Partial Detector Match"
            for item in results
        )
        print("Partial detector matches:", partial)
        print("No detector match:", len(results) - partial)
