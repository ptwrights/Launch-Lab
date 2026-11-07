import json

# Load our sensitive information categories
with open("data/hipaa_entities.json", "r") as file:
    data = json.load(file)

# Read the HIPAA law
with open("data/law_text.txt", "r", encoding="utf-8") as file:
    law_text = file.read()

# Search for each category in the law
print("Searching HIPAA for sensitive information...\n")

for entity in data["sensitive_entities"]:
    if entity.lower() in " ".join(law_text.lower().split()):
        print(f"FOUND: {entity}")
    else:
        print(f"NOT FOUND: {entity}")