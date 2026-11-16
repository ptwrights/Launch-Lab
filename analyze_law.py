
import ollama
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def analyze_hipaa():
    # Open the HIPAA text file
    file_path = BASE_DIR / "data" / "law_text.txt"

    with open(file_path, "r", encoding="utf-8") as file:
        law_text = file.read()

    # Find the HIPAA section listing identifiers
    search_text = "Social security numbers;"
    position = law_text.lower().find(search_text.lower())

    if position == -1:
        raise ValueError("Could not find the HIPAA identifier list.")

    # Extract the relevant section
    start = max(0, position - 1500)
    end = min(len(law_text), position + 1500)

    law_section = law_text[start:end]

    print("Analyzing HIPAA with Ollama...")

    # Ask Ollama to identify sensitive information
    response = ollama.chat(
        model="llama3.2:3b",
        format="json",
        options={"temperature": 0},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are analyzing the HIPAA Privacy Rule. "
                    "Identify only personal identifiers explicitly "
                    "listed in the provided legal text. "
                    "Do not include publication or compliance dates. "
                    "Return ONLY valid JSON in this format: "
                    '{"entities": [{"name": "identifier name", '
                    '"source_text": "exact supporting phrase"}]}. '
                    "Copy supporting phrases exactly from the text. "
                    "Do not invent information."
                )
            },
            {
                "role": "user",
                "content": f"Analyze this legal text:\n\n{law_section}"
            }
        ]
    )

    # Convert the AI response to Python data
    try:
        results = json.loads(response["message"]["content"])
    except json.JSONDecodeError:
        raise ValueError("Ollama did not return valid JSON.")

    # Verify supporting phrases
    verified_entities = []

    for entity in results.get("entities", []):
        name = entity.get("name", "")
        source_text = entity.get("source_text", "")

        if not isinstance(name, str) or not isinstance(source_text, str):
            continue

        if name and source_text and source_text.lower() in law_section.lower():
            verified_entities.append({
                "name": name,
                "source_text": source_text,
                "page": None
            })

    output = {
        "regulation": "HIPAA",
        "entities": verified_entities
    }

    # Save results
    with open(BASE_DIR / "analysis_results.json", "w") as file:
        json.dump(output, file, indent=4)

    return output


# Still allows the file to run independently
if __name__ == "__main__":
    results = analyze_hipaa()

    print("\nAnalysis saved to analysis_results.json")
    print("Verified entities:", len(results["entities"]))

    for entity in results["entities"]:
        print("-", entity["name"])




