
import streamlit as st
import pandas as pd
import json
import subprocess
import sys
from pathlib import Path

# Find the project folder
BASE_DIR = Path(__file__).resolve().parent

# Set up the dashboard
st.set_page_config(
    page_title="Regulatory AI Analyzer",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Regulatory AI Analyzer")

st.write(
    "AI-powered sensitive entity discovery "
    "and detector coverage mapping"
)

st.divider()

# Select regulation
regulation = st.selectbox(
    "Select a Regulation",
    ["HIPAA"]
)

st.info(
    "Prototype using HIPAA and a simulated detector "
    "inventory. Results do not represent actual "
    "NetApp detector coverage."
)

# Run the analysis
if st.button("Run AI Analysis", type="primary"):

    with st.spinner("Running AI analysis..."):

        try:
            # Step 1: Extract identifiers using Ollama
            analysis = subprocess.run(
                [sys.executable, "analyze_law.py"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=BASE_DIR
            )

            if analysis.returncode != 0:
                st.error("AI analysis failed.")
                st.code(analysis.stderr)
                st.stop()

            # Step 2: Compare identifiers with detectors
            mapping = subprocess.run(
                [sys.executable, "map_detectors.py"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=BASE_DIR
            )

            if mapping.returncode != 0:
                st.error("Detector mapping failed.")
                st.code(mapping.stderr)
                st.stop()

            # Step 3: Add candidate source citations
            citations = subprocess.run(
                [sys.executable, "add_citations.py"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=BASE_DIR
            )

            if citations.returncode != 0:
                st.error("Citation matching failed.")
                st.code(citations.stderr)
                st.stop()

            # Step 4: Generate candidate detection rules
            rules = subprocess.run(
                [sys.executable, "suggest_rules.py"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=BASE_DIR
            )

            if rules.returncode != 0:
                st.error("Rule suggestions failed.")
                st.code(rules.stderr)
                st.stop()

            st.success(
                "AI analysis, detector mapping, citations, "
                "and detection rules completed!"
            )

        except subprocess.TimeoutExpired:
            st.error(
                "The analysis timed out. "
                "Make sure Ollama is running."
            )
            st.stop()

        except Exception as error:
            st.error(f"Something went wrong: {error}")
            st.stop()

st.divider()

# Load results
results_path = BASE_DIR / "coverage_results.json"

if not results_path.exists():
    st.warning(
        "No results found. Click Run AI Analysis first."
    )
    st.stop()

with open(results_path, "r", encoding="utf-8") as file:
    results = json.load(file)

# Calculate coverage numbers
total = len(results)
covered = sum(item["covered"] for item in results)
gaps = total - covered

# Display overview
st.subheader("HIPAA Coverage Overview")

col1, col2, col3 = st.columns(3)

col1.metric("HIPAA Categories", total)
col2.metric("Covered", covered)
col3.metric("Potential Gaps", gaps)

st.divider()

# Create coverage table
st.subheader("Detector Coverage Report")

table_data = []

for item in results:
    table_data.append({
        "HIPAA Identifier": item["entity"],
        "Status": item["status"],
        "Regulatory Reference": item["regulatory_reference"],
        "PDF Page": item.get("page") or "Not found"
    })

df = pd.DataFrame(table_data)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Coverage is based on a simulated detector inventory. "
    "PDF citations are candidate matches and have not "
    "been independently verified."
)

st.divider()

# Display detection gaps
st.subheader("Potential Detection Gaps")

gap_results = [
    item for item in results
    if not item["covered"]
]

if gap_results:

    for item in gap_results:

        with st.expander(item["entity"]):

            st.write("**Status:** Potential Coverage Gap")

            st.write(
                "**Regulatory Reference:**",
                item["regulatory_reference"]
            )

            st.write(
                "**PDF Page:**",
                item.get("page") or "Not found"
            )

            # Display subcategories
            subcategories = item.get("subcategories", [])

            if subcategories:
                st.write("**Related Extracted Identifiers:**")

                for subcategory in subcategories:
                    st.write("-", subcategory)

            # Display supporting passage
            if item.get("source_excerpt"):
                st.write("**Candidate Source Passage:**")
                st.caption(item["source_excerpt"])
            else:
                st.write("No source passage found.")

            # Display suggested detection rule
            suggestion = item.get("suggested_rule")

            if suggestion:
                st.write("**Suggested Detection Method:**")
                st.write(suggestion["method"])

                if suggestion.get("pattern"):
                    st.write("**Example Detection Pattern:**")
                    st.code(
                        suggestion["pattern"],
                        language="text"
                    )

                st.caption(suggestion["notes"])
            else:
                st.write(
                    "No detection rule suggestion available."
                )

else:
    st.success(
        "No potential gaps found in the sample inventory."
    )

st.divider()

# Download results
st.subheader("Export Compliance Results")

json_output = json.dumps(results, indent=4)

st.download_button(
    label="Download JSON Report",
    data=json_output,
    file_name="hipaa_coverage_report.json",
    mime="application/json"
)

st.divider()

st.caption(
    "NetApp Launch Lab | Regulatory AI Analyzer Prototype"
)


