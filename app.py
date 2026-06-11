
from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import json
from datetime import datetime

from src.rag_pipeline import load_pipeline, analyze_message
from src.pdf_knowledge import load_pdf_system, add_pdf

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PDF REGISTRY — persistent storage of uploaded PDFs
# ─────────────────────────────────────────────────────────────────────────────

PDF_REGISTRY_FILE = os.path.join(
    "data",
    "pdf",
    "pdf_registry.json"
)

def load_pdf_registry():
    """Load the PDF registry from JSON file"""
    if os.path.exists(PDF_REGISTRY_FILE):
        try:
            with open(PDF_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARNING] Could not load PDF registry: {e}")
            return []
    return []

def save_pdf_registry(registry):
    """Save the PDF registry to JSON file"""
    try:
        with open(PDF_REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        print(f"[INFO] PDF registry saved with {len(registry)} entries")
    except IOError as e:
        print(f"[ERROR] Could not save PDF registry: {e}")

def add_pdf_to_registry(filename, pages_indexed, filepath):
    """Add a new PDF entry to the registry"""
    registry = load_pdf_registry()
    
    # Check if PDF already exists
    for pdf in registry:
        if pdf['name'] == filename:
            # Update existing entry
            pdf['pages'] = pages_indexed
            pdf['added_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            pdf['path'] = filepath
            save_pdf_registry(registry)
            return
    
    # Add new entry
    registry.append({
        'name': filename,
        'pages': pages_indexed,
        'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'path': filepath
    })
    save_pdf_registry(registry)

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP — load RAG pipeline once
# ─────────────────────────────────────────────────────────────────────────────

load_pipeline()
load_pdf_system()

# ─────────────────────────────────────────────────────────────────────────────
# DATASET STATS — computed from real dataset
# ─────────────────────────────────────────────────────────────────────────────

def get_dataset_stats():
    try:
        df = pd.read_excel(
        os.path.join(
            "data",
            "datasets",
            "master_dataset_preprocessed.xlsx"
        ),
        header=0
    )
        return {
            "total":      len(df),
            "phishing":   int((df['label'] == 'phishing').sum()),
            "legitimate": int((df['label'] == 'legitimate').sum()),
            "channels": {
                k: int(v) for k, v in df['channel'].value_counts().to_dict().items()
            },
            "languages": {
                "English": int((df['language'] == 'en').sum()),
                "Arabic":  int((df['language'] == 'ar').sum()),
                "French":  int((df['language'] == 'fr').sum()),
            },
            "attack_types": {
                k: int(v) for k, v in df['attack_type'].value_counts().to_dict().items()
            }
        }
    except Exception as e:
        print(f"[WARNING] Could not load dataset stats: {e}")
        return {
            "total": 3038, "phishing": 1359, "legitimate": 1679,
            "channels":      {"email": 644, "sms": 856, "url": 1264, "social_media": 274},
            "languages":     {"English": 1508, "Arabic": 899, "French": 631},
            "attack_types":  {"none": 1041, "brand_impersonation": 609, "credential_theft": 739,
                              "urgency": 368, "prize_scam": 185, "typosquatting": 24,
                              "malware_link": 18, "malicious_attachment": 10, "threat": 4}
        }

DATASET_STATS = get_dataset_stats()

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html', stats=DATASET_STATS)


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    text = data.get('text', '').strip()

    if not text:
        return jsonify({"error": "Please enter a message to analyze."}), 400

    if len(text) < 5:
        return jsonify({"error": "Message is too short to analyze."}), 400

    result = analyze_message(text)
    return jsonify(result)


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    """Upload a PDF as new knowledge base with persistent registry."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files are accepted."}), 400

    # Save the file
    upload_path = os.path.join("uploads", file.filename)
    os.makedirs("uploads", exist_ok=True)
    file.save(upload_path)
    
    print(f"[INFO] PDF saved: {upload_path}")

    # Add PDF to the separate PDF knowledge base
    try:
        chunks_added = add_pdf(upload_path)
        
        # Add to registry for persistence
        add_pdf_to_registry(file.filename, chunks_added, upload_path)
        
        return jsonify({
            "success": True,
            "message": f"PDF '{file.filename}' integrated into the RAG knowledge base.",
            "pages_indexed": chunks_added
        })
    except Exception as e:
        print(f"[ERROR] Failed to process PDF: {e}")
        return jsonify({
            "error": f"Failed to process PDF: {str(e)}"
        }), 500


@app.route('/get_pdfs', methods=['GET'])
def get_pdfs():
    """Return list of uploaded PDFs from registry."""
    registry = load_pdf_registry()
    
    # Format the response for the frontend
    pdfs = []
    for pdf in registry:
        pdfs.append({
            'name': pdf.get('name', 'Unknown'),
            'pages': pdf.get('pages', 0),
            'added_date': pdf.get('added_date', 'Unknown'),
            'path': pdf.get('path', '')
        })
    
    return jsonify({'pdfs': pdfs})


@app.route('/delete_pdf/<filename>', methods=['DELETE'])
def delete_pdf(filename):
    """Delete a PDF from the registry and optionally from disk."""
    registry = load_pdf_registry()
    
    # Find and remove the PDF from registry
    pdf_to_delete = None
    for pdf in registry:
        if pdf['name'] == filename:
            pdf_to_delete = pdf
            break
    
    if pdf_to_delete:
        registry.remove(pdf_to_delete)
        save_pdf_registry(registry)
        
        # Optional: Delete the actual file from disk
        if os.path.exists(pdf_to_delete['path']):
            os.remove(pdf_to_delete['path'])
            print(f"[INFO] Deleted PDF file: {pdf_to_delete['path']}")
        
        return jsonify({"success": True, "message": f"PDF '{filename}' deleted successfully."})
    
    return jsonify({"error": "PDF not found."}), 404


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    registry = load_pdf_registry()
    return jsonify({
        "status": "healthy",
        "pdf_count": len(registry),
        "stats": DATASET_STATS
    })


if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs("uploads", exist_ok=True)
    
    # Load existing PDFs from registry on startup
    registry = load_pdf_registry()
    print(f"[INFO] Loaded {len(registry)} PDFs from registry")
    
    app.run(debug=True, port=5000)