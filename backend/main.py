import subprocess
import sys

from pathlib import Path
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GapGuard AI API")

# Find the main Launch-Lab project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Allow our local React app to communicate with FastAPI
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

REPORT_FILES = {
    "hipaa": "coverage_results.json",
    "ccpa": "ccpa_coverage_results.json",
}


@app.get("/")
def home():
    return {"message": "GapGuard AI API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/regulations")
def get_regulations():
    return {
        "regulations": [
            {"id": "hipaa", "name": "HIPAA"},
            {"id": "ccpa", "name": "CCPA"},
        ]
    }


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

@app.post("/analyze/{regulation}")
def run_analysis(regulation: str):
    regulation = regulation.lower()

    if regulation not in REPORT_FILES:
        raise HTTPException(
            status_code=404,
            detail="Regulation not supported."
        )

    if regulation == "hipaa":
        commands = [
            ["rag_analysis.py"],
            ["map_detectors.py", "HIPAA"],
            ["add_citations.py"],
            ["suggest_rules.py"],
        ]
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
