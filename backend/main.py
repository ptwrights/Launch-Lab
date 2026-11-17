
import json
import subprocess
import sys
import uuid

from pathlib import Path

import fitz

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware


# ----------------------------------------
# APP SETUP
# ----------------------------------------

app = FastAPI(title="GapGuard AI API")

# Main Launch-Lab project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Folder for uploaded PDFs
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Maximum upload size: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024


# Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Existing analysis report files
REPORT_FILES = {
    "hipaa": "coverage_results.json",
    "ccpa": "ccpa_coverage_results.json",
}


# ----------------------------------------
# HOME
# ----------------------------------------

@app.get("/")
def home():
    return {
        "message": "GapGuard AI API is running"
    }


# ----------------------------------------
# HEALTH CHECK
# ----------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# ----------------------------------------
# AVAILABLE REGULATIONS
# ----------------------------------------

@app.get("/regulations")
def get_regulations():
    return {
        "regulations": [
            {
                "id": "hipaa",
                "name": "HIPAA"
            },
            {
                "id": "ccpa",
                "name": "CCPA"
            },
        ]
    }


# ----------------------------------------
# LOAD SAVED ANALYSIS RESULTS
# ----------------------------------------

@app.get("/results/{regulation}")
def get_results(regulation: str):

    regulation = regulation.lower()

    if regulation not in REPORT_FILES:
        raise HTTPException(
            status_code=404,
            detail="Regulation not supported."
        )

    file_path = BASE_DIR / REPORT_FILES[regulation]

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No analysis results found. Run the analysis first."
        )

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (OSError, json.JSONDecodeError) as error:
        print("Error loading results:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not load analysis results."
        )


# ----------------------------------------
# RUN EXISTING AI ANALYSIS
# ----------------------------------------

@app.post("/analyze/{regulation}")
def run_analysis(regulation: str):

    regulation = regulation.lower()

    if regulation not in REPORT_FILES:
        raise HTTPException(
            status_code=404,
            detail="Regulation not supported."
        )

    # HIPAA analysis pipeline
    if regulation == "hipaa":
        commands = [
            ["rag_analysis.py"],
            ["map_detectors.py", "HIPAA"],
            ["add_citations.py"],
            ["suggest_rules.py"],
        ]

    # CCPA analysis pipeline
    else:
        commands = [
            ["analyze_ccpa.py"],
            ["map_detectors.py", "CCPA"],
        ]

    try:
        for command in commands:
            subprocess.run(
                [sys.executable, *command],
                cwd=BASE_DIR,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )

        report_path = BASE_DIR / REPORT_FILES[regulation]

        with open(report_path, "r", encoding="utf-8") as file:
            results = json.load(file)

        return {
            "message": f"{regulation.upper()} analysis completed",
            "regulation": regulation,
            "results": results,
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Analysis timed out."
        )

    except subprocess.CalledProcessError as error:
        print("Analysis failed:", error.stderr)

        raise HTTPException(
            status_code=500,
            detail="AI analysis failed. Check the backend terminal."
        )

    except (OSError, json.JSONDecodeError) as error:
        print("Report error:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not load the generated report."
        )


# ----------------------------------------
# UPLOAD REGULATION PDF
# ----------------------------------------

@app.post("/upload-regulation")
async def upload_regulation(
    file: UploadFile = File(...)
):

    # Make sure the file has a PDF extension
    if (
        not file.filename
        or not file.filename.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # Check the file's declared content type
    if file.content_type not in (
        "application/pdf",
        "application/x-pdf",
    ):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must be a PDF."
        )

    # Create a unique document ID
    document_id = uuid.uuid4().hex

    # Generate a safe filename
    saved_filename = f"{document_id}.pdf"

    saved_path = UPLOAD_DIR / saved_filename

    file_size = 0

    try:
        # Save the PDF in chunks
        with open(saved_path, "xb") as output:

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                file_size += len(chunk)

                # Reject files larger than 20 MB
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="PDF exceeds the 20 MB upload limit."
                    )

                output.write(chunk)

        # Check the PDF signature
        with open(saved_path, "rb") as saved_file:
            signature = saved_file.read(5)

        if signature != b"%PDF-":
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid PDF."
            )

        # Check that PyMuPDF can open the file
        try:
            with fitz.open(saved_path) as pdf:

                if pdf.page_count == 0:
                    raise ValueError(
                        "PDF has no pages."
                    )

                if pdf.needs_pass:
                    raise ValueError(
                        "Password-protected PDFs are unsupported."
                    )

        except Exception:
            raise HTTPException(
                status_code=400,
                detail="PDF is unreadable, empty, or password-protected."
            )

        return {
            "message": "PDF uploaded successfully.",
            "document_id": document_id,
            "filename": file.filename,
            "file_size_bytes": file_size,
            "status": "uploaded",
        }

    except HTTPException:
        saved_path.unlink(missing_ok=True)
        raise

    except OSError as error:
        saved_path.unlink(missing_ok=True)

        print("Upload error:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not save uploaded PDF."
        )

    finally:
        await file.close()


# ----------------------------------------
# EXTRACT TEXT FROM UPLOADED PDF
# ----------------------------------------

@app.get("/extract-regulation/{document_id}")
def extract_regulation(document_id: str):

    # Validate document ID
    # Our upload endpoint generates 32-character hex IDs
    if (
        len(document_id) != 32
        or any(
            character not in "0123456789abcdef"
            for character in document_id
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID."
        )

    # Find the uploaded PDF
    file_path = UPLOAD_DIR / f"{document_id}.pdf"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Uploaded document not found."
        )

    try:
        pages = []

        # Open the PDF using PyMuPDF
        with fitz.open(file_path) as pdf:

            # Read every page
            for page_number, page in enumerate(
                pdf,
                start=1
            ):

                # Extract text from the page
                text = page.get_text("text")

                pages.append({
                    "page": page_number,
                    "text": text,
                })

        # Combine all page text
        full_text = "\n".join(
            page["text"]
            for page in pages
        )

        # Make sure the PDF contains extractable text
        if not full_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No extractable text found in the PDF."
            )

        # Return extraction information
        return {
            "document_id": document_id,
            "status": "extracted",
            "total_pages": len(pages),
            "total_characters": len(full_text),
            "text_preview": full_text[:1000],
        }

    except HTTPException:
        raise

    except (OSError, RuntimeError, ValueError) as error:
        print("PDF extraction error:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not extract PDF text."
        )

# ----------------------------------------
# ANALYZE UPLOADED REGULATION
# ----------------------------------------

@app.post("/analyze-upload/{document_id}")
def analyze_uploaded_regulation(document_id: str):

    if (
        len(document_id) != 32
        or any(
            c not in "0123456789abcdef"
            for c in document_id
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID."
        )

    pdf_path = (
        UPLOAD_DIR / f"{document_id}.pdf"
    )

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Uploaded PDF not found."
        )

    try:
        # Chunk the uploaded PDF
        subprocess.run(
            [
                sys.executable,
                "chunk_uploaded.py",
                document_id,
            ],
            cwd=BASE_DIR,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Run AI analysis
        subprocess.run(
            [
                sys.executable,
                "analyze_uploaded.py",
                document_id,
            ],
            cwd=BASE_DIR,
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )

        report_path = (
            BASE_DIR
            / "data"
            / "chunks"
            / f"{document_id}_coverage.json"
        )

        with open(
            report_path,
            "r",
            encoding="utf-8"
        ) as file:
            results = json.load(file)

        return {
            "message": "Uploaded regulation analyzed.",
            "document_id": document_id,
            "results": results,
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Analysis timed out."
        )

    except subprocess.CalledProcessError as error:
        print("Analysis error:", error.stderr)

        raise HTTPException(
            status_code=500,
            detail="Uploaded regulation analysis failed."
        )

    except (OSError, json.JSONDecodeError) as error:
        print("Report error:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not load uploaded analysis results."
        )


# ----------------------------------------
# GET UPLOADED ANALYSIS RESULTS
# ----------------------------------------

@app.get("/results-upload/{document_id}")
def get_uploaded_results(document_id: str):

    if (
        len(document_id) != 32
        or any(
            c not in "0123456789abcdef"
            for c in document_id
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID."
        )

    report_path = (
        BASE_DIR
        / "data"
        / "chunks"
        / f"{document_id}_coverage.json"
    )

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No analysis results found."
        )

    try:
        with open(
            report_path,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (OSError, json.JSONDecodeError):
        raise HTTPException(
            status_code=500,
            detail="Could not load results."
        )


