
import ollama
import json

# Open the HIPAA text file
with open("data/law_text.txt", "r", encoding="utf-8") as file:
    law_text = file.read()

# Find the HIPAA section listing sensitive identifiers
search_text = "Social security numbers;"

position = law_text.lower().find(search_text.lower())

if position == -1:
    print("Could not find the HIPAA identifier list.")
    exit()

# Extract text around the identifier list
start = max(0, position - 1500)
end = min(len(law_text), position + 1500)

law_section = law_text[start:end]

print("HIPAA section found!")
print("Analyzing with Ollama...")

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
    print("Error: Ollama did not return valid JSON.")
    exit()

# Verify that supporting phrases appear in the text
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

# Organize the final results
output = {
    "regulation": "HIPAA",
    "entities": verified_entities
}

# Save results to a JSON file
with open("analysis_results.json", "w") as file:
    json.dump(output, file, indent=4)

print("\nAnalysis saved to analysis_results.json")
print("Verified entities:", len(verified_entities))

# Display the extracted identifiers
print("\nExtracted HIPAA Identifiers:")

for entity in verified_entities:
    print("-", entity["name"])



