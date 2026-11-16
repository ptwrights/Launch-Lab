
import json
import fitz
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Paths to the CCPA PDF and output JSON
pdf_path = BASE_DIR / "data" / "laws" / "ccpa.pdf"
output_path = BASE_DIR / "ccpa_chunks.json"

# Each chunk contains approximately 1,000 characters
CHUNK_SIZE = 1000
OVERLAP = 150


def chunk_ccpa():

    chunks = []

    # Open the CCPA document
    with fitz.open(pdf_path) as pdf:

        for page_number, page in enumerate(pdf, start=1):

            text = page.get_text("text")
            text = " ".join(text.split())

            if not text:
                continue

            start = 0

            while start < len(text):

                end = min(start + CHUNK_SIZE, len(text))

                chunk_text = text[start:end]

                chunks.append({
                    "page": page_number,
                    "text": chunk_text
                })

                if end == len(text):
                    break

                start = end - OVERLAP

    # Save chunks to JSON
    with open(output_path, "w", encoding="utf-8") as file:

        json.dump(chunks, file, indent=4)

    print("CCPA document processed successfully!")
    print("Total chunks:", len(chunks))
    print("Saved to:", output_path)


if __name__ == "__main__":
    chunk_ccpa()
