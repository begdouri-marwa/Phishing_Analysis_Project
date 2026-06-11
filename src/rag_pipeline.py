
import os
import re
import json
from urllib.parse import urlparse
from openai import OpenAI

from src.retrieval_module import build_retrieval_system, retrieve
from src.pdf_knowledge import retrieve_pdf

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
import os

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# Global pipeline objects — loaded once at startup
_df          = None
_emb_model   = None
_faiss_index = None
_bm25        = None

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP — call once when Flask starts
# ─────────────────────────────────────────────────────────────────────────────

def load_pipeline():
    """Load dataset, embeddings, FAISS index and BM25. Call once at startup."""
    global _df, _emb_model, _faiss_index, _bm25
    print("[INFO] Loading RAG pipeline...")
    _df, _emb_model, _faiss_index, _bm25 = build_retrieval_system()
    print("[INFO] RAG pipeline ready.")

# ─────────────────────────────────────────────────────────────────────────────
# URL DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def is_url(text: str) -> bool:
    """Check if the input is a URL."""
    text = text.strip()
    return (
        text.startswith("http://") or
        text.startswith("https://") or
        text.startswith("www.")     or
        bool(re.match(r'^[\w\-]+\.[a-z]{2,}', text))
    )

# ─────────────────────────────────────────────────────────────────────────────
# URL ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

SUSPICIOUS_WORDS = [
    # English
    "verify", "verification", "secure", "security", "login", "signin",
    "account", "update", "click", "confirm", "banking", "payment",
    "paypal", "amazon", "apple", "microsoft", "support", "service",
    "suspend", "suspended", "urgent", "immediate", "action-required",
    "free", "winner", "won", "prize", "reward", "bonus",
    "password", "credential", "credentials", "reset", "recovery",
    "unlock", "locked", "access", "limited", "restricted",
    "alert", "warning", "notice", "billing", "invoice",

    # French
    "vérifier", "verification", "sécurisé", "sécurité", "connexion",
    "compte", "mise-a-jour", "miseajour", "cliquez", "cliquer",
    "confirmer", "confirmation", "bancaire", "paiement",
    "suspension", "suspendu", "urgent", "immédiat",
    "gratuit", "gagnant", "gain", "prix", "récompense",
    "mot-de-passe", "identifiant", "réinitialiser", "réactivation",
    "débloquer", "bloqué", "accès", "limité", "restreint",
    "alerte", "avertissement", "facture",

    # Arabic
    "توثيق", "تحقق", "تأكيد", "تفعيل",
    "حساب", "حسابك", "تسجيل", "دخول",
    "بنك", "بنكي", "دفع", "فاتورة",
    "تحديث", "تجديد", "إعادة", "إعادة-تعيين",
    "كلمة-السر", "كلمة-مرور", "رمز", "رمز-التحقق",
    "معلق", "موقوف", "إيقاف", "تعليق",
    "عاجل", "فوري", "تحذير", "تنبيه",
    "جائزة", "ربح", "هدية", "مجاني",
    "استرجاع", "استعادة", "تأكيد-الهوية"
]


SUSPICIOUS_TLDS = [
    # Très utilisés dans phishing / gratuits
    ".tk", ".ml", ".ga", ".cf", ".gq",

    # Cheap / spam fréquents
    ".xyz", ".top", ".club", ".online", ".site", ".store",
    ".website", ".space", ".fun", ".click", ".live",


    # Autres TLD parfois abusés
    ".work", ".support", ".review", ".party", ".trade",
    ".account", ".download", ".stream", ".loan", ".win",

    
]

def extract_url_features(url: str) -> dict:
    """Extract features from a URL for phishing detection."""
    parsed    = urlparse(url)
    domain    = parsed.netloc
    path      = parsed.path
    scheme    = parsed.scheme
    parts     = domain.split(".")
    subdomain = ".".join(parts[:-2]) if len(parts) > 2 else ""
    tld       = "." + parts[-1] if parts else ""

    return {
        "url":              url,
        "domain":           domain,
        "subdomain":        subdomain,
        "path":             path,
        "scheme":           scheme,
        "url_length":       len(url),
        "has_ip":           bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain)),
        "has_at":           "@" in url,
        "dash_count":       domain.count("-"),
        "subdomain_count":  len(parts) - 2 if len(parts) > 2 else 0,
        "is_https":         scheme == "https",
        "suspicious_tld":   tld in SUSPICIOUS_TLDS,
        "suspicious_words": [w for w in SUSPICIOUS_WORDS if w in url.lower()],
    }

def features_to_text(features: dict) -> str:
    """Convert URL features to readable text for the LLM prompt."""
    lines = [
        f"URL analyzed: {features['url']}",
        f"Domain: {features['domain']}",
        f"Subdomain: {features['subdomain'] or 'none'}",
        f"Path: {features['path'] or '/'}",
        f"Protocol: {features['scheme'].upper()}",
        f"Total length: {features['url_length']} characters",
        f"Contains IP address: {'yes' if features['has_ip'] else 'no'}",
        f"Contains @: {'yes' if features['has_at'] else 'no'}",
        f"Dashes in domain: {features['dash_count']}",
        f"Number of subdomains: {features['subdomain_count']}",
        f"HTTPS: {'yes' if features['is_https'] else 'no'}",
        f"Suspicious TLD: {'yes' if features['suspicious_tld'] else 'no'}",
        f"Suspicious words detected: {', '.join(features['suspicious_words']) if features['suspicious_words'] else 'none'}",
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_context(retrieved_df) -> str:
    """Format retrieved examples as context for the LLM."""
    context_parts = []
    for i, (_, row) in enumerate(retrieved_df.iterrows(), start=1):
        context_parts.append(f"""
Example {i}
Text: {row['text']}
Label: {row['label']}
Language: {row['language']}
Attack Type: {row['attack_type']}
Risk Level: {row['risk_level']}
""")
    return "\n".join(context_parts)

# ─────────────────────────────────────────────────────────────────────────────
# JSON EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(raw: str):
    """Extract JSON object from raw LLM response."""
    if not raw:
        return None
    # Remove <think> tags (qwen produces these)
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
    # Try ```json blocks first
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if m:
        return m.group(1)
    # Fall back to any JSON object
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        return m.group(0)
    return None

# ─────────────────────────────────────────────────────────────────────────────
# RAG ANALYZE — core function
# ─────────────────────────────────────────────────────────────────────────────

def rag_analyze(query: str, top_k: int = 5) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve similar cases from dataset
    2. Build context
    3. Send to LLM with enriched prompt
    4. Parse and return result
    """
    # Retrieve similar cases
# ======================================================
# DATASET RAG (YOUR ORIGINAL LOGIC)
    # ======================================================

    retrieved = retrieve(
        query,
        _emb_model,
        _faiss_index,
        _bm25,
        _df,
        top_k=top_k
    )

    dataset_context = build_context(retrieved)


    # ======================================================
    # PDF RAG (NEW INDEPENDENT KNOWLEDGE BASE)
    # ======================================================

    pdf_results = retrieve_pdf(
        query,
        top_k=3
    )


    pdf_context = ""

    if pdf_results:
        pdf_context = "\nPDF Knowledge:\n"

        for i, chunk in enumerate(pdf_results, 1):
            pdf_context += f"""
    Document {i}:
    {chunk}

    """


    # Final context
    context = dataset_context + pdf_context

    # Build enriched prompt
    prompt = f"""
You are a cybersecurity expert specialized in phishing detection.

You are an advanced cybersecurity expert specialized in phishing detection.

You have access to two sources of knowledge:

1. Historical phishing dataset:
- These are real examples of phishing and legitimate messages.
- Use them to compare patterns, language, links, impersonation attempts, and social engineering tactics.

2. Specialized cybersecurity PDF knowledge:
- These documents contain expert knowledge about advanced and modern phishing techniques.
- If the analyzed message matches a technique described in the PDF knowledge, you MUST explicitly identify and name the attack.
- Prefer precise cybersecurity terminology rather than generic categories.

Examples of advanced attacks that may appear:
- Business Email Compromise (BEC): executive impersonation, confidential financial requests, urgent wire transfers, secrecy, bypassing normal procedures.
- QR Phishing (Quishing): malicious QR codes redirecting users to fake login pages.
- MFA Fatigue Attack: repeated authentication requests designed to make users approve a malicious login.
- OAuth Consent Phishing: malicious applications requesting access to emails, files, contacts, or cloud accounts.
- AI Voice Phishing (Vishing): attackers using voice cloning or fake emergency calls to request money or sensitive information.

Retrieved Knowledge:
{context}

Analyze the following message carefully.

Message:
{query}

Use both the historical examples and the PDF knowledge before making your decision.
When a specialized attack is detected, clearly mention its official name in the attack_type and explanation.

Message:
{query}

Before classifying, check for:
1. Urgency language (URGENT, immediately, suspended, blocked)
2. Suspicious links or domains
3. Brand impersonation
4. Requests for credentials or personal data
5. Prize or reward scams

IMPORTANT:
- Return ONLY valid JSON, no markdown, no explanation outside JSON.
- Respond in the same language as the input message.
- If label is legitimate, risk_score must be between 0 and 30.

{{
  "label": "phishing|legitimate",
  "confidence": <float 0.0-1.0>,
  "risk_score": <int 0-100>,
  "language": "en|fr|ar",
  "attack_type": "credential_theft|brand_impersonation|urgency|prize_scam|threat|typosquatting|malware_link|none",
  "explanation": "one sentence explanation",
  "suspicious_elements": ["element1", "element2"],
  "recommendation": "recommended action"
}}
"""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity expert specialized in phishing detection. Always respond with valid JSON only. Never add text outside the JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            max_tokens=500
        )

        raw       = response.choices[0].message.content
        json_text = extract_json(raw)

        if json_text is None:
            raise ValueError("No JSON found in model response")

        parsed = json.loads(json_text)

        # Normalize confidence
        confidence = parsed.get("confidence", 0.0)
        if isinstance(confidence, str):
            confidence = {"low": 0.3, "medium": 0.6, "high": 0.9}.get(confidence.lower(), 0.0)
        try:
            confidence = float(confidence)
        except:
            confidence = 0.0
        parsed["confidence"] = round(max(0.0, min(1.0, confidence)), 2)

        # Normalize label
        label = str(parsed.get("label", "unknown")).lower().strip()
        parsed["label"] = "phishing" if "phishing" in label else "legitimate"

        # Add retrieved examples count
        parsed["retrieved_examples"] = len(retrieved)

        # Add similar cases for dashboard display
        parsed["similar_cases"] = retrieved[
            ["text", "label", "language", "attack_type", "risk_level", "channel"]
        ].to_dict(orient="records")

        # Map label to classification key (dashboard uses "classification")
        parsed["classification"] = parsed["label"]

        # Map recommendation to recommendations key (dashboard uses "recommendations")
        parsed["recommendations"] = parsed.get("recommendation", "")

        return parsed

    except Exception as e:
        return {
            "classification": "error",
            "label":          "error",
            "error":          str(e),
            "risk_score":     0,
            "explanation":    f"Analysis failed: {str(e)}",
            "suspicious_elements": [],
            "recommendations": "Please try again.",
            "similar_cases":   [],
        }

# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT — called by app.py
# ─────────────────────────────────────────────────────────────────────────────

def analyze_message(text: str) -> dict:
    """
    Main function called by app.py.
    Handles both regular messages and URLs.
    """
    text = text.strip()

    if is_url(text):
        # Extract URL features and convert to text for RAG
        features    = extract_url_features(text)
        url_text    = features_to_text(features)
        result      = rag_analyze(url_text)
        result["url_features"] = features
        result["channel"]      = "url"
    else:
        result          = rag_analyze(text)
        result["channel"] = "message"

    # Convert risk_score to risk_level for dashboard
    risk_score = result.get("risk_score", 0)
    try:
        risk_score = int(risk_score)
    except:
        risk_score = 0

    if risk_score >= 70:
        result["risk_level"] = "critical"
    elif risk_score >= 40:
        result["risk_level"] = "medium"
    else:
        result["risk_level"] = "low"

    # Convert confidence to percentage for dashboard
    result["confidence"] = int(result.get("confidence", 0) * 100)

    return result
