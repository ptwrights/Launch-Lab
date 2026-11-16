
import streamlit as st
import pandas as pd
import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="GapGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# DASHBOARD STYLING
# -------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #0B1713;
        color: #E8F1EB;
    }

    [data-testid="stSidebar"] {
        background-color: #10251C;
        border-right: 1px solid #294738;
    }

    [data-testid="stSidebar"] * {
        color: #E8F1EB;
    }

    h1, h2, h3 {
        color: #E8F1EB !important;
    }

    [data-testid="stMetric"] {
        background-color: #173126;
        border: 1px solid #345744;
        border-radius: 14px;
        padding: 18px;
    }

    [data-testid="stMetricLabel"] {
        color: #B6CCBC;
    }

    [data-testid="stMetricValue"] {
        color: #C0E6CB;
    }

    div.stButton > button[kind="primary"] {
        background-color: #4D9B70;
        color: #FFFFFF;
        border-radius: 10px;
        border: none;
        font-weight: 600;
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: #65B788;
    }

    [data-testid="stExpander"] {
        background-color: #142B21;
        border: 1px solid #345744;
        border-radius: 10px;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #345744;
        border-radius: 10px;
    }

    .dashboard-subtitle {
        color: #A9C5B3;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .section-caption {
        color: #9AB8A5;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------
# HELPER FUNCTIONS
# -------------------------

def load_json(filename):
    path = BASE_DIR / filename

    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def run_script(script, arguments=None, timeout=180):
    command = [sys.executable, script]

    if arguments:
        command.extend(arguments)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=BASE_DIR
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{script} failed:\n"
            f"{result.stderr or result.stdout}"
        )

    return result.stdout


# -------------------------
# SIDEBAR
# -------------------------

with st.sidebar:

    st.title("🛡️ GapGuard AI")

    st.caption("LAUNCH LAB | SECURITY INTELLIGENCE")

    st.divider()

    st.subheader("Analysis Settings")

    regulation = st.selectbox(
        "Select Regulation",
        ["HIPAA", "CCPA"]
    )

    st.caption(
        "HIPAA — Healthcare privacy identifiers"
        if regulation == "HIPAA"
        else "CCPA — California consumer privacy"
    )

    st.divider()

    run_analysis = st.button(
        "▶ Run AI Analysis",
        type="primary",
        use_container_width=True
    )

    st.divider()

    st.markdown("**Analysis Engine**")

    st.caption("LLM: Ollama / Llama 3.2")
    st.caption("Retrieval: BM25 + FAISS")
    st.caption("Mapping: Simulated detector inventory")

    st.divider()

    st.caption("NetApp CodePath Innovation Sprint")


# -------------------------
# PAGE HEADER
# -------------------------

st.title("GapGuard AI")

st.markdown(
    '<p class="dashboard-subtitle">'
    'AI-powered regulatory intelligence, sensitive data '
    'discovery, and detector coverage analysis.'
    '</p>',
    unsafe_allow_html=True
)

st.info(
    "Prototype using a simulated detector inventory. "
    "Results do not represent actual NetApp detector "
    "coverage or establish legal compliance."
)


# -------------------------
# RUN ANALYSIS
# -------------------------

if run_analysis:

    with st.spinner(
        f"Running {regulation} AI analysis..."
    ):

        try:

            if regulation == "HIPAA":

                # Use the working HIPAA RAG pipeline
                run_script(
                    "rag_analysis.py",
                    timeout=240
                )

                # Map the verified RAG output
                from map_detectors import map_detectors

                rag_results = load_json(
                    "rag_analysis_results.json"
                )

                if rag_results is None:
                    raise RuntimeError(
                        "HIPAA RAG results were not created."
                    )

                map_detectors(
                    analysis=rag_results,
                    regulation="HIPAA"
                )

                # Keep existing HIPAA enrichment scripts
                run_script(
                    "add_citations.py",
                    timeout=30
                )

                run_script(
                    "suggest_rules.py",
                    timeout=30
                )

            else:

                # CCPA RAG extraction
                run_script(
                    "analyze_ccpa.py",
                    timeout=240
                )

                # CCPA detector mapping
                run_script(
                    "map_detectors.py",
                    arguments=["CCPA"],
                    timeout=30
                )

            st.success(
                f"{regulation} analysis completed successfully!"
            )

        except subprocess.TimeoutExpired:
            st.error(
                "The analysis timed out. "
                "Check that Ollama is running."
            )

        except Exception as error:
            st.error(str(error))


# -------------------------
# LOAD SELECTED RESULTS
# -------------------------

if regulation == "HIPAA":
    results = load_json("coverage_results.json")
    analysis_data = load_json("rag_analysis_results.json")
    expected_categories = 18

else:
    results = load_json("ccpa_coverage_results.json")
    analysis_data = load_json("ccpa_analysis_results.json")
    expected_categories = 10


if results is None:
    st.warning(
        f"No {regulation} results found. "
        "Click Run AI Analysis in the sidebar."
    )
    st.stop()


# -------------------------
# OVERVIEW METRICS
# -------------------------

st.subheader(f"{regulation} Analysis Overview")

total = len(results)

if regulation == "HIPAA":

    covered = sum(
        item.get("covered", False)
        for item in results
    )

    gaps = total - covered

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Categories Analyzed", total)
    col2.metric("Covered", covered)
    col3.metric("Potential Gaps", gaps)
    col4.metric(
        "Detector Match Rate",
        f"{covered / total * 100:.0f}%"
        if total else "0%"
    )

else:

    partial = sum(
        item.get("status") == "Partial Detector Match"
        for item in results
    )

    unmatched = sum(
        item.get("status") == "No Detector Match"
        for item in results
    )

    missing_extraction = max(
        0,
        expected_categories - total
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Categories Extracted", total)
    col2.metric("Partial Matches", partial)
    col3.metric("No Detector Match", unmatched)
    col4.metric("Not Yet Extracted", missing_extraction)


st.divider()


# -------------------------
# DASHBOARD TABS
# -------------------------

tab1, tab2, tab3 = st.tabs([
    "📊 Coverage Overview",
    "🔎 Regulatory Evidence",
    "📥 Export Results"
])


# -------------------------
# TAB 1: COVERAGE
# -------------------------

with tab1:

    st.subheader("Detector Coverage")

    if regulation == "HIPAA":

        chart_data = pd.DataFrame({
            "Status": [
                "Covered",
                "Potential Gap"
            ],
            "Categories": [
                covered,
                gaps
            ]
        })

    else:

        chart_data = pd.DataFrame({
            "Status": [
                "Partial Detector Match",
                "No Detector Match",
                "Not Yet Extracted"
            ],
            "Categories": [
                partial,
                unmatched,
                missing_extraction
            ]
        })

    st.bar_chart(
        chart_data,
        x="Status",
        y="Categories",
        color="#67B98A"
    )

    st.divider()

    st.subheader("Detector Mapping Report")

    search_term = st.text_input(
        "Search categories",
        placeholder="Search by identifier, status, or reference..."
    )

    table_data = []

    for item in results:

        table_data.append({
            "Category": item.get("entity", ""),
            "Status": item.get("status", ""),
            "Detector": item.get("detector") or "None",
            "Regulatory Reference": item.get(
                "regulatory_reference", ""
            ),
            "PDF Page": item.get("page") or "Not found"
        })

    df = pd.DataFrame(table_data)

    if search_term:

        mask = df.astype(str).apply(
            lambda column: column.str.contains(
                search_term,
                case=False,
                regex=False
            )
        ).any(axis=1)

        df = df[mask]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Detector matches are based on a simulated inventory. "
        "CCPA partial matches do not establish full category coverage."
    )


# -------------------------
# TAB 2: REGULATORY EVIDENCE
# -------------------------

with tab2:

    st.subheader("Regulatory Evidence & Detection Gaps")

    if regulation == "HIPAA":

        display_results = [
            item for item in results
            if not item.get("covered", False)
        ]

    else:

        display_results = results

    for item in display_results:

        entity = item.get("entity", "Unknown")
        status = item.get("status", "Unknown")

        with st.expander(
            f"{entity} — {status}"
        ):

            st.write("**Status:**", status)

            st.write(
                "**Regulatory Reference:**",
                item.get("regulatory_reference", "N/A")
            )

            st.write(
                "**PDF Page:**",
                item.get("page") or "Not found"
            )

            st.write(
                "**Matching Detector:**",
                item.get("detector") or "None"
            )

            subcategories = item.get(
                "subcategories", []
            )

            if subcategories:

                st.write("**Extracted Categories:**")

                for subcategory in subcategories:
                    st.write("•", subcategory)

            source_text = (
                item.get("source_excerpt")
                or item.get("source_text")
            )

            if source_text:

                st.write("**Supporting Source Text:**")
                st.caption(source_text)

            suggestion = item.get("suggested_rule")

            if suggestion:

                st.write("**Suggested Detection Method:**")
                st.write(
                    suggestion.get("method", "N/A")
                )

                if suggestion.get("pattern"):
                    st.code(
                        suggestion["pattern"],
                        language="text"
                    )

                if suggestion.get("notes"):
                    st.caption(
                        suggestion["notes"]
                    )

            elif status in (
                "Gap",
                "No Detector Match"
            ):

                st.caption(
                    "No automated detection rule suggestion "
                    "is available for this category."
                )

    if regulation == "CCPA":

        st.warning(
            "CCPA extraction currently covers "
            f"{total} of {expected_categories} "
            "provision-level categories. "
            "Unextracted categories are not counted "
            "as detector gaps."
        )


# -------------------------
# TAB 3: EXPORT
# -------------------------

with tab3:

    st.subheader("Export Analysis")

    st.write(
        "Download the detector mapping report "
        "for further review."
    )

    st.download_button(
        label="Download Coverage Report (JSON)",
        data=json.dumps(
            results,
            indent=4
        ),
        file_name=(
            f"{regulation.lower()}_coverage_report.json"
        ),
        mime="application/json",
        use_container_width=True
    )

    if analysis_data:

        st.download_button(
            label="Download AI Extraction Results (JSON)",
            data=json.dumps(
                analysis_data,
                indent=4
            ),
            file_name=(
                f"{regulation.lower()}_ai_analysis.json"
            ),
            mime="application/json",
            use_container_width=True
        )


# -------------------------
# FOOTER
# -------------------------

st.divider()

st.caption(
    "Regulatory AI Analyzer | NetApp CodePath Launch Lab"
)

st.caption(
    "Research prototype • Hybrid retrieval • "
    "LLM-assisted extraction • Simulated detector mapping"
)



