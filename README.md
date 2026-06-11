# PhishGuard — Multilingual Phishing Detection System

PhishGuard is a Flask-based NLP application designed to detect phishing and suspicious social engineering content in English, French, and Arabic. The project combines dataset retrieval, URL feature analysis, and optional PDF knowledge ingestion into a retrieval-augmented generation (RAG) workflow.

**Database spreadsheet:** https://docs.google.com/spreadsheets/d/1BjB1DXOQ5qawsTU2jFloD6pzr1v31xBa/edit?usp=drive_link&ouid=112024764227967577583&rtpof=true&sd=true

## What this project does

- Detects phishing and legitimate messages across email, SMS, URL, and social media channels
- Uses a hybrid retrieval pipeline with FAISS embeddings and BM25 search
- Builds contextual analysis from similar dataset examples
- Extracts URL features and suspicious tokens for better phishing detection
- Supports PDF knowledge base uploads for extending domain knowledge
- Displays dataset dashboard metrics and recent analysis history

## 📁 Repository structure

- `app.py` — Flask web server and API endpoints for analysis, PDF upload, and registry management
- `requirements.txt` — Python packages required to run the application
- `requirements.py` — helper script to inspect and install requirements
- `src/` — core backend implementation
  - `src/rag_pipeline.py` — RAG orchestration, URL detection, and analysis logic
  - `src/retrieval_module.py` — dataset retrieval system using `faiss`, `sentence-transformers`, and `rank_bm25`
  - `src/pdf_knowledge.py` — PDF extraction, chunk creation, embedding, and retrieval support
- `templates/` — Jinja2 HTML templates for the user interface
- `static/` — frontend styles and client-side JavaScript
- `data/` — dataset files, indexes, PDF registry, and persistent PDF knowledge artifacts
- `uploads/` — uploaded PDF storage
- `notebooks/` — experimental notebooks used for RAG research, analysis, and benchmarking
- `benchmarking/` — CSV results and summary files from retrieval and model benchmarking

## Additional project artifacts

These files are not required to run the web app, but they document how the system was developed and evaluated:

- `notebooks/RagRetrieval.ipynb` — notebook for prototyping retrieval and RAG workflows
- `notebooks/llm/LLM_Benchmarking.ipynb` — notebook used for LLM benchmarking and analysis
- `benchmarking/benchmark_by_language.csv` — language-specific retrieval benchmarking results
- `benchmarking/benchmark_predictions.csv` — raw prediction evaluation records
- `benchmarking/benchmark_summary.csv` — aggregated benchmark metrics
- `benchmarking/benchmarking_retrieval.csv` — retrieval-specific performance data

## Key features

- Multilingual phishing detection: English, French, Arabic
- Hybrid retrieval with FAISS and BM25
- URL feature extraction for suspicious domain and path signals
- Similar-case explanation and recommendation output
- PDF upload workflow for extending knowledge coverage
- Dashboard and history overview in the web UI

## Team Contributions

- **BEGDOURI TERRAF Marwa** — dataset curation, synthetic data generation, dashboard and PDF knowledge upload, and dataset search for URLs.
- **AMAR BAKAR Lareibiya** — retrieval module development, multilingual dataset preprocessing, social media and SMS data search support and Create the embeddings, faiss_index, and bm25_index files.
- **ELMIRI Imad** — LLM design, prompt engineering, benchmarking, and Gmail sample analysis.
- **HAFDOUNE Oussama** — SMS analysis support, URL scoring logic, integration testing, and SMS dataset search.
- **RAFIQ Ilias** — RAG pipeline orchestration, normal SMS flow, retrieval integration, and final system wiring.

## Dataset Search Breakdown

| Member | Data Sources / Search Scope |
| --- | --- |
| BEGDOURI TERRAF Marwa | URLs |
| AMAR BAKAR Lareibiya | Social media and SMS dataset search |
| ELMIRI Imad | Gmail samples, LLM benchmark data |
| HIAFDOUNE Oussama | SMS dataset search and SMS suspicion patterns |
| RAFIQ Ilias | SMS dataset search and gmails |

## Installation

1. Create a Python virtual environment:

```bash
python -m venv venv
```

2. Activate the environment:

- Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

- Windows CMD:

```cmd
venv\Scripts\activate.bat
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## ▶ Run the application

```bash
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Usage

- Paste a suspicious message, SMS, URL, or social media text into the analyzer
- Click **Analyze Now** to inspect phishing risk and get actionable recommendations
- Upload a PDF in the Knowledge Base tab to extend the system with new document knowledge
- View the Dashboard for dataset statistics, language distribution, and risk summaries
- Use the History tab to review session analysis results

## Notes

- The app expects the dataset file at `data/datasets/master_dataset_preprocessed.xlsx`.
- The retrieval pipeline uses `data/indexes/embeddings.npy`, `data/indexes/faiss_index.bin`, and `data/indexes/bm25_index.pkl`.
- Database spreadsheet: https://docs.google.com/spreadsheets/d/1BjB1DXOQ5qawsTU2jFloD6pzr1v31xBa/edit?usp=drive_link&ouid=112024764227967577583&rtpof=true&sd=true
- PDF knowledge files are stored under `data/pdf/` and registered in `data/pdf/pdf_registry.json`.
- `src/pdf_knowledge.py` relies on `PyMuPDF` (`fitz`) for PDF text extraction.
- `src/retrieval_module.py` relies on `faiss`, `numpy`, `pandas`, `sentence-transformers`, and `rank_bm25`.

## Dependency summary

`requirements.txt` now includes:

- `flask==3.0.0`
- `pandas==2.1.0`
- `numpy>=1.26.0`
- `sentence-transformers`
- `rank_bm25`
- `PyMuPDF`
- `openai`
- `faiss-cpu`

## Tips

- If you need GPU acceleration, replace `faiss-cpu` with the appropriate FAISS GPU package.
- If `sentence-transformers` installation fails, ensure your `torch` package matches your OS and Python version.
- Keep `uploads/` available for incoming PDFs and use `data/pdf/` for persisted knowledge.
- The notebooks and benchmarking files are useful for development, analysis, and improving the retrieval pipeline.

## Contributing

This project is ready for improvement. Suggested next steps:

- add environment variable support for API keys and model configuration
- improve dataset preprocessing and index rebuilding scripts
- enhance frontend feedback and analysis detail
- add better logging, error handling, and automated tests
## lien de la video

https://drive.google.com/drive/folders/1j9NyRbp5bCI7yxiauPTc51YTrcGF-I4c?usp=drive_link
---

Built to combine phishing detection, dataset retrieval, and explainable NLP analysis across multiple languages.
