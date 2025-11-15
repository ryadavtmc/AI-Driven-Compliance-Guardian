######################### USING POLICY RULES ##################################

#!/usr/bin/env python3
#!/usr/bin/env python3
"""
AI-Driven Compliance Guardian (Policy-Aware Hybrid Final)
---------------------------------------------------------
Combines:
  • Regex-based PII/Secret detection  (regex_detector)
  • BERT-based Secret Classifier      (bert_secret_clf_v2)
  • DistilBERT PII NER                (pii_ner_v3)
  • Hybrid ML Classifier              (ml_classifier/hybrid)
  • Policy-driven decisions           (config/policy_rules.yaml)
"""

import os, re, json, math, yaml, torch, joblib, numpy as np
from scipy.sparse import hstack, csr_matrix
from transformers import AutoTokenizer, AutoModel, AutoModelForTokenClassification
from safetensors.torch import load_file

# ==========================================================
#  Defensive Imports
# ==========================================================
try:
    from app.regex_detector import detect as regex_detect, mask_text
except ModuleNotFoundError:
    from regex_detector import detect as regex_detect, mask_text

# ==========================================================
#  Paths & Config
# ==========================================================
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS = os.path.join(BASE, "models")
CONFIG_PATH = os.path.join(BASE, "config", "policy_rules.yaml")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ==========================================================
#  Load Policy Config
# ==========================================================
def load_policy():
    """Load YAML-based policy configuration."""
    try:
        with open(CONFIG_PATH, "r") as f:
            policy = yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️ Failed to load policy file: {e}")
        policy = {}
    return {
        "BLOCK": set(policy.get("block_categories", [])),
        "MASK": set(policy.get("mask_categories", [])),
        "PII_POLICY": policy.get("pii_entity_policy", {}),
        "THRESHOLDS": policy.get("thresholds", {"secret_block": 0.7, "ml_unsafe": 0.65})
    }

POLICY = load_policy()
BLOCK_CATEGORIES = POLICY["BLOCK"]
MASK_CATEGORIES = POLICY["MASK"]
PII_POLICY = POLICY["PII_POLICY"]
THRESHOLDS = POLICY["THRESHOLDS"]

# ==========================================================
#  Utility Functions
# ==========================================================
def entropy(s: str) -> float:
    """Calculate Shannon entropy."""
    if not s:
        return 0.0
    p = [s.count(c) / len(s) for c in set(s)]
    return -sum(pi * math.log(pi, 2) for pi in p)

def extra_features(text: str):
    """Extra contextual features for secret classification."""
    looks_jwt = 1 if re.search(r"eyJ[a-zA-Z0-9_-]{10,}\.", text) else 0
    looks_key = 1 if re.search(r"(sk_|gh[pousr]_)", text) else 0
    return [len(text), entropy(text), looks_jwt, looks_key]

# ==========================================================
#  Secret Classifier (DistilRoBERTa)
# ==========================================================
class SecretClassifier(torch.nn.Module):
    def __init__(self, model_name="distilroberta-base", extra_dim=4, num_labels=2):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = torch.nn.Dropout(0.3)
        hidden = self.bert.config.hidden_size
        self.classifier = torch.nn.Linear(hidden + extra_dim, num_labels)
    def forward(self, input_ids, attention_mask, features):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        x = torch.cat([cls, features], dim=1)
        x = self.dropout(x)
        return self.classifier(x)

SECRET_MODEL_PATH = os.path.join(MODELS, "secret_detector")
SECRET_TOKENIZER = AutoTokenizer.from_pretrained("distilroberta-base")
SECRET_MODEL = SecretClassifier().to(DEVICE)
safe_path = os.path.join(SECRET_MODEL_PATH, "model.safetensors")
bin_path = os.path.join(SECRET_MODEL_PATH, "pytorch_model.bin")

if os.path.exists(safe_path):
    state_dict = load_file(safe_path, device="cpu")
elif os.path.exists(bin_path):
    state_dict = torch.load(bin_path, map_location=DEVICE)
else:
    raise FileNotFoundError(f"No weights found in {SECRET_MODEL_PATH}")
SECRET_MODEL.load_state_dict(state_dict, strict=False)
SECRET_MODEL.eval()

# ==========================================================
#  PII NER (DistilBERT)
# ==========================================================
PII_MODEL_PATH = os.path.join(MODELS, "pii_ner")
PII_TOKENIZER = AutoTokenizer.from_pretrained(PII_MODEL_PATH)
PII_MODEL = AutoModelForTokenClassification.from_pretrained(PII_MODEL_PATH).to(DEVICE)
PII_MODEL.eval()
PII_LABELS = ["O","B-NAME","I-NAME","B-EMAIL","I-EMAIL","B-PHONE","B-ADDRESS","B-ID"]


def detect_pii(text: str):
    """
    Detect tokens and labels for PII entities.
    Includes lightweight false-positive filtering for numeric/short/common tokens.
    """
    enc = PII_TOKENIZER(text, truncation=True, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        logits = PII_MODEL(**enc).logits
    preds = torch.argmax(logits, dim=2)[0].cpu().numpy()
    tokens = PII_TOKENIZER.convert_ids_to_tokens(enc["input_ids"][0])

    entities, labeled_entities = [], []

    # --- False-positive suppression rules ---
    IGNORE_TOKENS = {
        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "a", "an", "the", "and", "of", "in", "on", "for", "to", "with", "by",
        "num", "number", "digit", "id", "section", "part", "item"
    }

    MIN_TOKEN_LEN = 2  # avoid masking single-character tokens
    MAX_NUMERIC_RATIO = 0.5  # avoid numeric-heavy tokens like '1234' or 'id123'

    for i, p in enumerate(preds):
        if p < len(PII_LABELS):
            label = PII_LABELS[p]
            token = tokens[i].replace("##", "")  # Clean subword token

            if label == "O":
                continue

            # --- Ignore false positives ---
            if token.lower() in IGNORE_TOKENS:
                continue

            if len(token.strip()) < MIN_TOKEN_LEN:
                continue

            # Skip purely numeric tokens
            if re.fullmatch(r"\d+", token):
                continue

            # Skip tokens where >50% of characters are digits
            if sum(c.isdigit() for c in token) / max(len(token), 1) > MAX_NUMERIC_RATIO:
                continue

            # Skip punctuation-like fragments
            if re.fullmatch(r"[\W_]+", token):
                continue

            entities.append(token)
            labeled_entities.append({"token": token, "label": label})

    # Deduplicate to prevent redundant masking
    return list(set(entities)), labeled_entities

# ==========================================================
#  Hybrid ML Classifier
# ==========================================================
ML_MODEL_DIR = os.path.join(MODELS, "ml_classifier")
vectorizer = joblib.load(os.path.join(ML_MODEL_DIR, "tfidf.pkl"))
models = {
    m: joblib.load(os.path.join(ML_MODEL_DIR, f"{m}.pkl"))
    for m in ["ensemble", "random_forest"]
    if os.path.exists(os.path.join(ML_MODEL_DIR, f"{m}.pkl"))
}
THRESHOLD_ML = THRESHOLDS.get("ml_unsafe", 0.65)

def ml_numeric_features(texts):
    rows = []
    for t in texts:
        t = str(t).strip()
        rows.append([
            len(t)/500.0,
            len(t.split())/100.0,
            entropy(t),
            sum(c.isdigit() for c in t)/max(len(t),1),
            len(re.findall(r"[^A-Za-z0-9\s]",t))/max(len(t),1)
        ])
    return np.asarray(rows, dtype=np.float32)*10.0

def ml_classify_text(text):
    """Classify with hybrid ensemble (auto-align feature size)."""
    tfidf = vectorizer.transform([text])
    num = ml_numeric_features([text])
    X = hstack([tfidf, num])

    model = models.get("ensemble")
    if not model:
        return {"label": "safe", "confidence": 0.0, "model": "none"}

    # --- Fix feature size mismatch automatically ---
    expected = getattr(model, "n_features_in_", None)
    if expected:
        current = X.shape[1]
        if current < expected:
            X = hstack([X, csr_matrix((1, expected - current))])
        elif current > expected:
            X = X[:, :expected]

    probs = model.predict_proba(X)[0]
    unsafe_prob = probs[1]
    label = "unsafe" if unsafe_prob >= THRESHOLD_ML else "safe"
    return {"label": label, "confidence": round(float(unsafe_prob), 3), "model": "ensemble"}

# ==========================================================
#  DETECT SECRET
# ==========================================================
def detect_secret(text: str):
    enc = SECRET_TOKENIZER(text, truncation=True, padding="max_length", max_length=128, return_tensors="pt")
    feats = torch.tensor([extra_features(text)], dtype=torch.float)
    with torch.no_grad():
        logits = SECRET_MODEL(enc["input_ids"].to(DEVICE), enc["attention_mask"].to(DEVICE), feats.to(DEVICE))
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
    score = probs[1]
    return {
        "is_secret": score >= THRESHOLDS.get("secret_block", 0.7),
        "confidence": round(float(score), 3),
        "source": "bert_secret_clf_v2"
    }

# ==========================================================
#  POLICY DECISION
# ==========================================================
# def decide_policy(regex_matches, secret_pred, pii_labeled, ml_pred):
#     """Decide final action using regex, ML, and PII labels."""
#     block_found = any(f.name in BLOCK_CATEGORIES for f in regex_matches)
#     mask_found = any(f.name in MASK_CATEGORIES for f in regex_matches)
#     secret_flag = secret_pred["is_secret"]
#     ml_flag = ml_pred["label"] == "unsafe"

#     # PII Policy-based masking/blocking
#     pii_mask_flag = any(
#         any(key in label["label"].upper() and PII_POLICY.get(key) == "mask"
#             for key in PII_POLICY.keys())
#         for label in pii_labeled
#     )
#     pii_block_flag = any(
#         any(key in label["label"].upper() and PII_POLICY.get(key) == "block"
#             for key in PII_POLICY.keys())
#         for label in pii_labeled
#     )

#     if block_found or secret_flag or ml_flag or pii_block_flag:
#         return "block"
#     if mask_found or pii_mask_flag:
#         return "mask"
#     return "allow"

def decide_policy(regex_matches, secret_pred, pii_labeled, ml_pred):
    """
    Decide final compliance action (block / mask / allow)
    using regex category, severity, ML classifier, and PII policy.
    """

    # --- Regex-based findings ---
    block_found = any(
        f.name in BLOCK_CATEGORIES
        or f.category == "Secret"
        or f.severity in {"critical", "high"}
        for f in regex_matches
    )

    mask_found = any(
        f.name in MASK_CATEGORIES
        or f.category == "PII"
        or (f.category == "Network" and f.severity in {"medium"})
        for f in regex_matches
    )

    # --- ML / Secret classifier flags ---
    secret_flag = secret_pred.get("is_secret", False)
    ml_flag = ml_pred.get("label", "safe") == "unsafe"

    # --- PII Entity Policies (from NER labels) ---
    pii_mask_flag = any(
        any(key in label["label"].upper() and PII_POLICY.get(key) == "mask"
            for key in PII_POLICY.keys())
        for label in pii_labeled
    )

    pii_block_flag = any(
        any(key in label["label"].upper() and PII_POLICY.get(key) == "block"
            for key in PII_POLICY.keys())
        for label in pii_labeled
    )

    # --- Decision priority ---
    if block_found or secret_flag or ml_flag or pii_block_flag:
        return "block"
    if mask_found or pii_mask_flag:
        return "mask"
    return "allow"

# ==========================================================
#  Unified Analysis
# ==========================================================
def analyze_text(text: str):
    regex_matches = regex_detect(text)
    secret_pred = detect_secret(text)
    pii_entities, pii_labeled = detect_pii(text)
    ml_pred = ml_classify_text(text)
    action = decide_policy(regex_matches, secret_pred, pii_labeled, ml_pred)

    masked_text = text
    if action == "mask":
        if regex_matches:
            masked_text = mask_text(masked_text, regex_matches, strategy="partial")
        for ent in pii_entities:
            if ent.strip():
                masked_text = re.sub(rf"\b{re.escape(ent)}\b", "[REDACTED_PII]", masked_text, flags=re.I)

    return {
        "input": text,
        "masked_output": masked_text if action == "mask" else None,
        "regex_findings": [f.name for f in regex_matches],
        "secret_confidence": secret_pred["confidence"],
        "ml_confidence": ml_pred["confidence"],
        "pii_entities": pii_entities,
        "pii_labels": pii_labeled,
        "action": action,
        "sources": ["regex", "bert_secret_clf_v2", "pii_ner_v3", ml_pred["model"]],
    }

# ==========================================================
#  Safe JSON Convert
# ==========================================================
def safe_convert(obj):
    if isinstance(obj, (bool, int, float, str)) or obj is None:
        return obj
    if isinstance(obj, (list, tuple)):
        return [safe_convert(x) for x in obj]
    if isinstance(obj, dict):
        return {k: safe_convert(v) for k, v in obj.items()}
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            return str(obj)
    if hasattr(obj, "__dict__"):
        return safe_convert(vars(obj))
    return str(obj)

# ==========================================================
#  CLI Test
# ==========================================================
if __name__ == "__main__":
    print("🧠 Compliance Guardian — Policy-Aware Unified Inference")
    print("Type text to analyze (or 'exit' to quit')\n")
    while True:
        text = input("💬 Enter text: ").strip()
        if text.lower() in {"exit", "quit"}:
            break
        result = analyze_text(text)
        print(json.dumps(safe_convert(result), indent=2, ensure_ascii=False))