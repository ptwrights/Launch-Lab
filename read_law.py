import pymupdf

# Open the PDF
document = pymupdf.open("data/laws/hipaa.pdf")

# Create a text file to store the law
with open("data/law_text.txt", "w", encoding="utf-8") as file:

    # Go through every page
    for page_number, page in enumerate(document):
        text = page.get_text()

        # Save the page number and its text
        file.write(f"\n--- Page {page_number + 1} ---\n")
        file.write(text)

document.close()

print("Law text saved successfully!")