
import json
import ollama

# Load chunks from the HIPAA document
with open("hipaa_chunks.json", "r") as file:
    chunks = json.load(file)

keywords = ["social security numbers", "medical record numbers"]

matching_chunk = None

for chunk in chunks:
    text = chunk["text"].lower()

    if any(keyword in text for keyword in keywords):
        matching_chunk = chunk
        break

if matching_chunk is None:
    print("No matching passage found.")
else:
    page_number = matching_chunk["page"]

    prompt = f"""
    Extract sensitive information categories explicitly
    mentioned in this HIPAA passage.

    Return ONLY valid JSON in this format:

    {{
        "entities": [
            {{
                "name": "Entity name",
                "source_text": "Exact supporting phrase"
            }}
        ]
    }}

    Do not invent categories or supporting phrases.
    Only use the passage provided.

    HIPAA passage:
    {matching_chunk["text"]}
    """

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {"role": "user", "content": prompt}
        ],
        format="json"
    )

    try:
        result = json.loads(response["message"]["content"])

        verified_entities = []

        for entity in result.get("entities", []):
            name = entity.get("name", "")
            source_text = entity.get("source_text", "")

            # Only keep results with an exact phrase in the passage
            if source_text and source_text.lower() in matching_chunk["text"].lower():
                verified_entities.append({
                    "name": name,
                    "source_text": source_text,
                    "page": page_number
                })

        output = {
            "regulation": "HIPAA",
            "entities": verified_entities
        }

        with open("analysis_results.json", "w") as file:
            json.dump(output, file, indent=4)

        print("Analysis saved to analysis_results.json")
        print("Verified entities:", len(verified_entities))
        print(json.dumps(output, indent=4))

    except (json.JSONDecodeError, TypeError, KeyError) as error:
        print("Could not process AI response:", error)


