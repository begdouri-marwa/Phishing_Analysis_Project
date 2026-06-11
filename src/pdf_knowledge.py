import os
import json
import fitz
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ======================================================
# PDF KNOWLEDGE STORAGE
# ======================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PDF_DATA_DIR = os.path.join(
    BASE_DIR,
    "data",
    "pdf"
)

os.makedirs(PDF_DATA_DIR, exist_ok=True)

PDF_CHUNKS_FILE = os.path.join(
    PDF_DATA_DIR,
    "pdf_chunks.json"
)

PDF_FAISS_FILE = os.path.join(
    PDF_DATA_DIR,
    "pdf_faiss.bin"
)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


# Global objects
pdf_chunks = []
pdf_index = None
embed_model = None


# ======================================================
# LOAD MODEL
# ======================================================

def load_pdf_system():
    global embed_model, pdf_index, pdf_chunks

    print("[PDF] Loading PDF knowledge system...")

    embed_model = SentenceTransformer(MODEL_NAME)

    # Load previous chunks
    if os.path.exists(PDF_CHUNKS_FILE):
        with open(PDF_CHUNKS_FILE, "r", encoding="utf-8") as f:
            pdf_chunks = json.load(f)
        print(f"[PDF] Loaded {len(pdf_chunks)} chunks")
    else:
        pdf_chunks = []


    # Load FAISS index
    if os.path.exists(PDF_FAISS_FILE):
        pdf_index = faiss.read_index(PDF_FAISS_FILE)
        print("[PDF] FAISS index loaded")
    else:
        pdf_index = None
        print("[PDF] New empty PDF index created")


# ======================================================
# EXTRACT TEXT FROM PDF
# ======================================================

def extract_pdf_text(path):
    document = fitz.open(path)

    text = ""

    for page in document:
        text += page.get_text() + "\n"

    return text


# ======================================================
# SPLIT TEXT INTO CHUNKS
# ======================================================

def chunk_text(text, chunk_size=500):
    chunks = []

    text = text.replace("\n", " ").strip()

    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]

        if len(chunk) > 50:
            chunks.append(chunk)

    return chunks


# ======================================================
# ADD NEW PDF TO KNOWLEDGE BASE
# ======================================================

def add_pdf(pdf_path):
    global pdf_chunks, pdf_index


    print(f"[PDF] Processing {pdf_path}")


    # 1 Extract text
    text = extract_pdf_text(pdf_path)


    # 2 Create chunks
    chunks = chunk_text(text)

    if not chunks:
        return 0


    # 3 Create embeddings
    vectors = embed_model.encode(
        chunks,
        convert_to_numpy=True
    )


    vectors = vectors.astype("float32")


    # Normalize for cosine similarity
    faiss.normalize_L2(vectors)


    # 4 Create index first time
    if pdf_index is None:
        dimension = vectors.shape[1]
        pdf_index = faiss.IndexFlatIP(dimension)


    # 5 Add vectors
    pdf_index.add(vectors)


    # 6 Store text chunks
    pdf_chunks.extend(chunks)


    # 7 Save everything

    with open(PDF_CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            pdf_chunks,
            f,
            ensure_ascii=False,
            indent=2
        )


    faiss.write_index(
        pdf_index,
        PDF_FAISS_FILE
    )


    print(f"[PDF] Added {len(chunks)} chunks")


    return len(chunks)


# ======================================================
# RETRIEVE PDF KNOWLEDGE
# ======================================================

def retrieve_pdf(query, top_k=3):

    if pdf_index is None or len(pdf_chunks) == 0:
        return []


    vector = embed_model.encode(
        [query],
        convert_to_numpy=True
    )

    vector = vector.astype("float32")

    faiss.normalize_L2(vector)


    scores, indices = pdf_index.search(
        vector,
        top_k
    )


    results = []


    for idx in indices[0]:

        if idx < len(pdf_chunks):
            results.append(pdf_chunks[idx])


    return results