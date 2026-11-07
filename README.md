# Regulatory AI Analyzer

An AI-powered prototype for identifying sensitive information categories in HIPAA regulations and comparing them against a simulated detector inventory.

## Technologies
- Python
- Streamlit
- PyMuPDF
- Ollama with Llama 3.2
- JSON

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/ptwrights/Launch-Lab.git
cd Launch-Lab
```

**2. Create a Python virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, activate with `.venv\Scripts\activate` instead.

**3. Install Python dependencies**

```bash
python -m pip install -r requirements.txt
```

**4. Install Ollama**

Download Ollama from https://ollama.com/download and install it.

Then download the model:

```bash
ollama pull llama3.2:3b
```

Make sure the Ollama service is running.

**5. Run the application**

```bash
python -m streamlit run app.py
```

Open the local URL displayed in your terminal, usually `http://localhost:8501`.

## How to Use

1. Select HIPAA.
2. Click **Run AI Analysis**.
3. Review the identifier categories and detector coverage.
4. Expand a potential gap to see candidate citations and suggested detection methods.
5. Download the JSON report.

## Important Limitations

This is a prototype using a selected HIPAA passage and a simulated detector inventory. It does not assess actual NetApp detector coverage or certify HIPAA compliance.

PDF citation matches are approximate, and suggested detection rules require independent verification and testing.
