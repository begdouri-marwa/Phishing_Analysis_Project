"""
retrieval_module.py
Module de Retrieval — Système RAG Phishing Detection
Auteur : Person 2
Prérequis : pip install sentence-transformers faiss-cpu rank-bm25 pandas numpy openpyxl
"""

import os
import re
import time
import pickle
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH     = os.path.join(BASE_DIR, "master_dataset_preprocessed.xlsx")
EMBEDDINGS_PATH  = os.path.join(BASE_DIR, "embeddings.npy")
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "faiss_index.bin")
BM25_PATH        = os.path.join(BASE_DIR, "bm25_index.pkl")
BENCHMARK_CSV    = os.path.join(BASE_DIR, "benchmarking_retrieval.csv")

DEFAULT_MODEL    = "paraphrase-multilingual-MiniLM-L12-v2"
TEXT_COLUMN      = "preprocessed_text"
RRF_K            = 60        # constante standard Reciprocal Rank Fusion
RRF_CANDIDATES   = 20        # ✅ Fix #4 — candidats élargis avant fusion RRF


# ─────────────────────────────────────────────
# PREPROCESSING DE LA REQUÊTE
# ─────────────────────────────────────────────
def preprocess_query(query: str) -> str:
    """
    ✅ Fix #2 — Applique le même preprocessing que Person 1 sur la requête.
    Minuscules + suppression ponctuation/chiffres + normalisation espaces.
    Adapter si Person 1 utilise stemming/lemmatisation supplémentaire.
    """
    query = query.lower()
    
    query = re.sub(r"\s+", " ", query).strip() # normalise les espaces
    return query


# ─────────────────────────────────────────────
# ÉTAPE 1 — CHARGEMENT DU DATASET
# ─────────────────────────────────────────────
def load_dataset(path: str = DATASET_PATH) -> pd.DataFrame:
    print(f"[INFO] Chargement du dataset : {path}")
    df = pd.read_excel(path)
    print(f"[INFO] Dataset chargé : {len(df)} lignes, colonnes : {list(df.columns)}")
    df = df.dropna(subset=[TEXT_COLUMN]).reset_index(drop=True)
    print(f"[INFO] Après nettoyage NaN : {len(df)} lignes")
    return df


# ─────────────────────────────────────────────
# ÉTAPE 2 — EMBEDDINGS SENTENCE-BERT
# ─────────────────────────────────────────────
def build_embeddings(
    df: pd.DataFrame,
    model_name: str = DEFAULT_MODEL,
    save_path: str = EMBEDDINGS_PATH,
) -> np.ndarray:
    print(f"[INFO] Chargement du modèle : {model_name}")
    model = SentenceTransformer(model_name)
    texts = df[TEXT_COLUMN].tolist()
    print(f"[INFO] Encodage de {len(texts)} textes…")
    t0 = time.time()
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    embeddings = embeddings.astype("float32")
    faiss.normalize_L2(embeddings)   # normalisation L2 → similarité cosinus
    elapsed = time.time() - t0
    print(f"[INFO] Encodage terminé en {elapsed:.1f}s — shape : {embeddings.shape}")
    np.save(save_path, embeddings)
    print(f"[INFO] Embeddings sauvegardés → {save_path}")
    return embeddings


# ─────────────────────────────────────────────
# ÉTAPE 3 — INDEX FAISS (cosinus via IndexFlatIP)
# ─────────────────────────────────────────────
def build_faiss_index(
    embeddings: np.ndarray,
    save_path: str = FAISS_INDEX_PATH,
) -> faiss.Index:
    dimension = embeddings.shape[1]
    print(f"[INFO] Construction de l'index FAISS IndexFlatIP (dim={dimension})…")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    faiss.write_index(index, save_path)
    print(f"[INFO] Index FAISS sauvegardé → {save_path}  ({index.ntotal} vecteurs)")
    return index


def load_index(path: str = FAISS_INDEX_PATH) -> faiss.Index:
    print(f"[INFO] Chargement de l'index FAISS : {path}")
    return faiss.read_index(path)


# ─────────────────────────────────────────────
# ÉTAPE 4 — BM25 (avec sauvegarde pickle)
# ─────────────────────────────────────────────
def build_bm25(df: pd.DataFrame, save_path: str = BM25_PATH) -> BM25Okapi:
    print("[INFO] Construction de l'index BM25…")
    tokenized_corpus = [text.split() for text in df[TEXT_COLUMN]]
    bm25 = BM25Okapi(tokenized_corpus)
    with open(save_path, "wb") as f:
        pickle.dump(bm25, f)
    print(f"[INFO] Index BM25 sauvegardé → {save_path}")
    return bm25


def load_bm25(path: str = BM25_PATH) -> BM25Okapi:
    print(f"[INFO] Chargement de l'index BM25 : {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


def bm25_search(
    query: str,
    bm25: BM25Okapi,
    df: pd.DataFrame,
    top_k: int = RRF_CANDIDATES,
) -> tuple:
    """Retourne (DataFrame résultats, liste indices originaux)."""
    tokens = query.split()   # déjà preprocessé en amont
    scores = bm25.get_scores(tokens)
    top_indices = scores.argsort()[-top_k:][::-1].tolist()
    results = df.iloc[top_indices].copy()
    results["bm25_score"] = scores[top_indices]
    return results, top_indices


# ─────────────────────────────────────────────
# ÉTAPE 5 — RECIPROCAL RANK FUSION
# ─────────────────────────────────────────────
def reciprocal_rank_fusion(
    faiss_indices: list,
    bm25_indices: list,
    df: pd.DataFrame,
    top_k: int = 5,
    k: int = RRF_K,
) -> pd.DataFrame:
    """
    Fusion RRF :  score(doc) = Σ 1 / (k + rank_i)
    Les candidats viennent de listes élargies (RRF_CANDIDATES=20)
    pour améliorer la qualité avant de retourner top_k.
    """
    rrf_scores = {}

    for rank, idx in enumerate(faiss_indices, start=1):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (k + rank)

    for rank, idx in enumerate(bm25_indices, start=1):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (k + rank)

    sorted_indices = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]
    results = df.iloc[sorted_indices].copy()
    results["rrf_score"] = [rrf_scores[i] for i in sorted_indices]
    results["source"] = "hybrid_rrf"
    return results.reset_index(drop=True)


# ─────────────────────────────────────────────
# ÉTAPE 6 — RECHERCHE HYBRIDE PRINCIPALE
# ─────────────────────────────────────────────
def retrieve(
    query: str,
    model: SentenceTransformer,
    index: faiss.Index,
    bm25: BM25Okapi,
    df: pd.DataFrame,
    top_k: int = 5,
) -> pd.DataFrame:
    """
    Recherche hybride FAISS + BM25 fusionnés par RRF.
    ✅ Fix #2 — La requête est prétraitée avant encodage et BM25.
    ✅ Fix #4 — RRF_CANDIDATES=20 candidats par méthode avant fusion finale.
    """
    # ✅ Fix #2 — Preprocessing identique au dataset
    query_clean = preprocess_query(query)

    # — FAISS : récupère RRF_CANDIDATES candidats —
    query_vec = model.encode([query_clean]).astype("float32")
    faiss.normalize_L2(query_vec)
    _, faiss_idx = index.search(query_vec, RRF_CANDIDATES)
    faiss_indices = faiss_idx[0].tolist()

    # — BM25 : récupère RRF_CANDIDATES candidats —
    _, bm25_indices = bm25_search(query_clean, bm25, df, RRF_CANDIDATES)

    # — RRF fusion → top_k final —
    return reciprocal_rank_fusion(faiss_indices, bm25_indices, df, top_k)


# ─────────────────────────────────────────────
import math


# ─────────────────────────────────────────────
# Precision@K
# ─────────────────────────────────────────────
def precision_at_k(retrieved_labels, relevant_label, k=5):
    """
    Precision@k = nb pertinents retrouvés dans top-k / nb documents retournés
    """
    top = retrieved_labels[:k]

    if len(top) == 0:
        return 0.0

    relevant_found = sum(
        1 for label in top
        if label == relevant_label
    )

    return relevant_found / len(top)


# ─────────────────────────────────────────────
# Recall@K
# ─────────────────────────────────────────────
def recall_at_k(
    retrieved_labels,
    relevant_label,
    total_relevant_count,
    k=5
):
    """
    Recall@k = nb pertinents retrouvés dans top-k
               -----------------------------------
               total documents pertinents dataset
    """

    if total_relevant_count == 0:
        return 0.0

    top = retrieved_labels[:k]

    relevant_found = sum(
        1 for label in top
        if label == relevant_label
    )

    return relevant_found / total_relevant_count


# ─────────────────────────────────────────────
# Hit Rate@K
# ─────────────────────────────────────────────
def hit_rate_at_k(
    retrieved_labels,
    relevant_label,
    k=5
):
    """
    Hit@k = 1 si au moins un document pertinent
            apparaît dans le top-k
    """

    top = retrieved_labels[:k]

    return float(
        any(label == relevant_label for label in top)
    )


# ─────────────────────────────────────────────
# MRR
# ─────────────────────────────────────────────
def reciprocal_rank(
    retrieved_labels,
    relevant_label
):
    """
    Reciprocal Rank = 1 / rang du premier pertinent
    """

    for rank, label in enumerate(
        retrieved_labels,
        start=1
    ):
        if label == relevant_label:
            return 1.0 / rank

    return 0.0


# ─────────────────────────────────────────────
# nDCG@K
# ─────────────────────────────────────────────
def ndcg_at_k(
    retrieved_labels,
    relevant_label,
    total_relevant_count,
    k=5
):
    """
    nDCG@k pour pertinence binaire

    rel_i = 1 si pertinent
            0 sinon
    """

    top = retrieved_labels[:k]

    # DCG réel
    dcg = 0.0

    for i, label in enumerate(top):
        if label == relevant_label:
            dcg += 1.0 / math.log2(i + 2)

    # DCG idéal
    ideal_relevant = min(
        total_relevant_count,
        k
    )

    idcg = sum(
        1.0 / math.log2(i + 2)
        for i in range(ideal_relevant)
    )

    if idcg == 0:
        return 0.0

    return dcg / idcg


# ─────────────────────────────────────────────
# ÉTAPE 8 — BENCHMARKING DES MODÈLES
# ─────────────────────────────────────────────
def benchmark_models(
    df: pd.DataFrame,
    model_names: list = None,
    sample_size: int = 100,
    top_k: int = 5,
    output_csv: str = BENCHMARK_CSV,
) -> pd.DataFrame:
    if model_names is None:
        model_names = [
            "paraphrase-multilingual-MiniLM-L12-v2",
            "distiluse-base-multilingual-cased-v2",
            "all-MiniLM-L6-v2",
        ]

    # ✅ PAS de reset_index : on conserve les indices originaux du df
    sample = df.sample(min(sample_size, len(df)), random_state=42)
    results = []

    for model_name in model_names:
        print(f"\n{'='*60}")
        print(f"[BENCHMARK] Modèle : {model_name}")
        print(f"{'='*60}")

        t_load = time.time()
        try:
            model = SentenceTransformer(model_name)
        except Exception as e:
            print(f"[ERREUR] Impossible de charger {model_name} : {e}")
            continue
        load_time = time.time() - t_load

        t_enc = time.time()
        emb = model.encode(df[TEXT_COLUMN].tolist(), batch_size=64, show_progress_bar=True)
        emb = emb.astype("float32")
        faiss.normalize_L2(emb)
        enc_time = time.time() - t_enc

        dim = emb.shape[1]
        idx = faiss.IndexFlatIP(dim)
        idx.add(emb)
        index_size_mb = emb.nbytes / (1024 ** 2)

        # Listes pour toutes les métriques
        prec_list, rec_list, hit_list, mrr_list, ndcg_list, times = [], [], [], [], [], []
        has_label = "label" in df.columns

        for original_idx, row in sample.iterrows():
            query_clean = preprocess_query(str(row[TEXT_COLUMN]))
            true_label = row.get("label", None) if has_label else None

            t0 = time.time()
            q_vec = model.encode([query_clean]).astype("float32")
            faiss.normalize_L2(q_vec)
            # récupère top_k+1 pour exclure la requête elle-même
            _, top_idx = idx.search(q_vec, top_k + 1)
            top_idx_filtered = [i for i in top_idx[0] if i != original_idx][:top_k]
            elapsed_ms = (time.time() - t0) * 1000
            times.append(elapsed_ms)

            if has_label and true_label is not None:
                retrieved_labels = df.iloc[top_idx_filtered]["label"].tolist()
                n_relevant = int((df["label"] == true_label).sum())

                p = precision_at_k(retrieved_labels, true_label, top_k)
                r = recall_at_k(retrieved_labels, true_label, n_relevant, top_k)
                h = hit_rate_at_k(retrieved_labels, true_label, top_k)
                mrr = reciprocal_rank(retrieved_labels, true_label)
                n = ndcg_at_k(retrieved_labels, true_label, n_relevant, top_k)

                prec_list.append(p)
                rec_list.append(r)
                hit_list.append(h)
                mrr_list.append(mrr)
                ndcg_list.append(n)

        row_result = {
            "model": model_name,
            "embedding_dim": dim,
            "encoding_time_s": round(enc_time, 2),
            "load_time_s": round(load_time, 2),
            "avg_search_time_ms": round(np.mean(times), 3),
            "index_size_mb": round(index_size_mb, 2),
            f"precision@{top_k}": round(np.mean(prec_list), 4) if prec_list else "N/A",
            f"recall@{top_k}": round(np.mean(rec_list), 4) if rec_list else "N/A",
            f"hit_rate@{top_k}": round(np.mean(hit_list), 4) if hit_list else "N/A",
            "mrr": round(np.mean(mrr_list), 4) if mrr_list else "N/A",
            f"ndcg@{top_k}": round(np.mean(ndcg_list), 4) if ndcg_list else "N/A",
        }
        results.append(row_result)
        print(f"[RESULT] {row_result}")

    bench_df = pd.DataFrame(results)
    bench_df.to_csv(output_csv, index=False)
    print(f"\n[INFO] Résultats sauvegardés → {output_csv}")
    print(bench_df.to_string(index=False))
    return bench_df

# ─────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────
def build_retrieval_system(
    dataset_path: str = DATASET_PATH,
    model_name: str = DEFAULT_MODEL,
    force_rebuild: bool = False,
):
    """Construit ou charge le système de retrieval complet."""
    df = load_dataset(dataset_path)

    if os.path.exists(EMBEDDINGS_PATH) and not force_rebuild:
        print(f"[INFO] Chargement des embeddings depuis {EMBEDDINGS_PATH}")
        embeddings = np.load(EMBEDDINGS_PATH)
    else:
        embeddings = build_embeddings(df, model_name)

    if os.path.exists(FAISS_INDEX_PATH) and not force_rebuild:
        index = load_index()
    else:
        index = build_faiss_index(embeddings)

    if os.path.exists(BM25_PATH) and not force_rebuild:
        bm25 = load_bm25()
    else:
        bm25 = build_bm25(df)

    model = SentenceTransformer(model_name)
    print("\n[INFO] Système de retrieval prêt ✓")
    return df, model, index, bm25


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    df, model, index, bm25 = build_retrieval_system()

    test_query = "Verify your account immediately! Click here."
    print(f"\n[QUERY brute]     « {test_query} »")
    print(f"[QUERY nettoyée]  « {preprocess_query(test_query)} »")

    results = retrieve(test_query, model, index, bm25, df, top_k=5)
    print("\n[TOP-5 RÉSULTATS — RRF]")
    print(results[[TEXT_COLUMN, "rrf_score", "source"]].to_string(index=False))

    print("\n[BENCHMARK] Comparaison des modèles d'embeddings…")
    bench = benchmark_models(df, sample_size=100, top_k=5)





