
import json
import sys
from pathlib import Path

import fitz


BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "data" / "uploads"

CHUNK_DIR = BASE_DIR / "data" / "chunks"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 1000
OVERLAP = 150


def chunk_uploaded(document_id):

    # Validate the document ID
    if (
        len(document_id) != 32
        or any(
            char not in "0123456789abcdef"
            for char in document_id
        )
    ):
        raise ValueError("Invalid document ID.")

    # Find the uploaded PDF
    pdf_path = UPLOAD_DIR / f"{document_id}.pdf"

    if not pdf_path.exists():
        raise FileNotFoundError(
            "Uploaded PDF not found."
        )

    # Each uploaded document gets its own chunk file
    output_path = CHUNK_DIR / f"{document_id}_chunks.json"

    chunks = []

    with fitz.open(pdf_path) as pdf:

        for page_number, page in enumerate(pdf, start=1):

            text = page.get_text("text")

            # Remove extra whitespace
            text = " ".join(text.split())

            if not text:
                continue

            start = 0

            while start < len(text):

                end = min(
                    start + CHUNK_SIZE,
                    len(text)
                )

                chunk_text = text[start:end]

                chunks.append({
                    "document_id": document_id,
                    "page": page_number,
                    "text": chunk_text
                })

                if end == len(text):
                    break

                start = end - OVERLAP

    if not chunks:
        raise ValueError(
            "No extractable text found in the PDF."
        )

    # Save the chunks
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(chunks, file, indent=4)

    print("Uploaded PDF processed successfully!")
    print("Document ID:", document_id)
    print("Total chunks:", len(chunks))
    print("Saved to:", output_path)

    return chunks


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            "Usage: python chunk_uploaded.py <document_id>"
        )
        sys.exit(1)

    document_id = sys.argv[1]

    chunk_uploaded(document_id)
