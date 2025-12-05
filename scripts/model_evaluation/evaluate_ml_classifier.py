#!/usr/bin/env python3
"""
ML Classifier Evaluation — Hybrid RF-Weighted (v3)
==================================================
Evaluates trained ensemble using held-out test data.
Saves metrics, confusion matrix, ROC, and PR curves to:
    evaluation/ml_classifier/
"""

import os, json, time, joblib, gc, warnings, re   # 👈 ADD re HERE
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from scipy.sparse import hstack, csr_matrix
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, roc_curve,
    precision_recall_curve, average_precision_score, f1_score, accuracy_score,
    log_loss, brier_score_loss
)
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
BASE_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/ml_classifier"
MODEL_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/models/ml_classifier"
EVAL_DIR  = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/evaluation/ml_classifier"
os.makedirs(EVAL_DIR, exist_ok=True)

RNG = 42
DTYPE = np.float32

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def entropy(s):
    if not s: return 0.0
    p = [s.count(c)/len(s) for c in set(s)]
    return -sum(pi * np.log2(pi) for pi in p)

def numeric_features(texts):
    """Generate the same 13 numeric + regex-based features used in training."""
    rows = []
    for t in texts:
        t = str(t).strip()
        num_chars = len(t)
        num_words = len(t.split())
        avg_word_len = num_chars / max(num_words, 1)
        token_density = num_words / max(num_chars, 1)
        entropy_val = entropy(t)
        digit_density = sum(c.isdigit() for c in t) / max(num_chars, 1)
        symbol_density = len(re.findall(r"[^A-Za-z0-9\s]", t)) / max(num_chars, 1)

        # PII pattern flags (amplified ×5 as in training)
        looks_jwt   = bool(re.search(r"eyJ[a-zA-Z0-9_-]{10,}\.", t))
        looks_key   = bool(re.search(r"(sk_|gh[pousr]_)", t))
        looks_ssn   = bool(re.search(r"\b\d{3}-\d{2}-\d{4}\b", t))
        looks_cc    = bool(re.search(r"\b(?:\d[ -]*?){13,16}\b", t))
        looks_email = bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t))
        looks_phone = bool(re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", t))

        rows.append([
            num_chars / 500.0, num_words / 100.0, avg_word_len / 10.0,
            token_density, entropy_val, digit_density, symbol_density,
            5*int(looks_jwt), 5*int(looks_key), 5*int(looks_ssn),
            5*int(looks_cc), 5*int(looks_email), 5*int(looks_phone)
        ])
    X = np.asarray(rows, dtype=DTYPE)
    return X * 10.0

def load_jsonl(path):
    data = []
    with open(path, "r") as f:
        for line in f:
            try: data.append(json.loads(line))
            except: continue
    return pd.DataFrame(data)

# ------------------------------------------------------------
# LOAD ARTIFACTS
# ------------------------------------------------------------
print("📦 Loading saved artifacts...")
ensemble = joblib.load(os.path.join(MODEL_DIR, "ensemble.pkl"))
tfidf = joblib.load(os.path.join(MODEL_DIR, "tfidf.pkl"))
le = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
print("✅ Ensemble, TF-IDF, and LabelEncoder loaded")

# ------------------------------------------------------------
# LOAD TEST DATA
# ------------------------------------------------------------
TEST_PATH = os.path.join(BASE_DIR, "augmented_safe_unsafe.jsonl")  # adjust if needed
df = load_jsonl(TEST_PATH)
df = df.dropna(subset=["text", "label"]).sample(5000, random_state=RNG)
print(f"📂 Loaded {len(df):,} test samples")

y_true = le.transform(df["label"])
texts  = df["text"].astype(str).tolist()

# ------------------------------------------------------------
# BUILD FEATURES (TF-IDF + NUMERIC)
# ------------------------------------------------------------
print("🔎 Building features...")
tfidf_test = tfidf.transform(tqdm(texts, desc="TF-IDF (test)"))
num_test = numeric_features(texts)
scaler = StandardScaler(with_mean=False)
num_test_scaled = scaler.fit_transform(num_test)
X_test = hstack([tfidf_test, csr_matrix(num_test_scaled)], format="csr")
print(f"✅ Feature matrix shape: {X_test.shape}")

# ------------------------------------------------------------
# PREDICT
# ------------------------------------------------------------
print("🚀 Running inference...")
y_pred = ensemble.predict(X_test)
y_proba = None
try:
    y_proba = ensemble.predict_proba(X_test)
except Exception:
    print("⚠️ Ensemble does not support predict_proba(); skipping probability-based metrics.")

# ------------------------------------------------------------
# METRICS
# ------------------------------------------------------------
print("\n📊 Classification Report:")
report = classification_report(y_true, y_pred, target_names=le.classes_, digits=4)
print(report)

acc = accuracy_score(y_true, y_pred)
f1 = f1_score(y_true, y_pred, average="weighted")
metrics = {
    "accuracy": acc,
    "f1_weighted": f1,
    "precision_recall_f1_report": report
}

if y_proba is not None:
    roc_auc = roc_auc_score(y_true, y_proba[:,1])
    pr_auc = average_precision_score(y_true, y_proba[:,1])
    brier = brier_score_loss(y_true, y_proba[:,1])
    lloss = log_loss(y_true, y_proba)
    metrics.update({"roc_auc": roc_auc, "pr_auc": pr_auc, "brier_score": brier, "log_loss": lloss})

# Save JSON summary
with open(os.path.join(EVAL_DIR, "metrics_summary.json"), "w") as f:
    json.dump(metrics, f, indent=2)
print("💾 Metrics saved → metrics_summary.json")

# ------------------------------------------------------------
# VISUALS
# ------------------------------------------------------------
# 1️⃣ Confusion Matrix
cm = confusion_matrix(y_true, y_pred)
plt.figure(figsize=(6,5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=le.classes_, yticklabels=le.classes_)
plt.title("Confusion Matrix — ML Classifier (Hybrid v3)")
plt.xlabel("Predicted")
plt.ylabel("True")
plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "confusion_matrix.png"))
plt.close()

# 2️⃣ ROC Curve
if y_proba is not None:
    fpr, tpr, _ = roc_curve(y_true, y_proba[:,1])
    plt.figure(figsize=(6,5))
    plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"AUC = {roc_auc:.3f}")
    plt.plot([0,1],[0,1],"--",color="gray")
    plt.title("ROC Curve — ML Classifier (Hybrid v3)")
    plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(EVAL_DIR, "roc_curve.png"))
    plt.close()

# 3️⃣ Precision-Recall Curve
if y_proba is not None:
    prec, rec, _ = precision_recall_curve(y_true, y_proba[:,1])
    plt.figure(figsize=(6,5))
    plt.plot(rec, prec, color="purple", lw=2, label=f"PR-AUC = {pr_auc:.3f}")
    plt.title("Precision-Recall Curve — ML Classifier (Hybrid v3)")
    plt.xlabel("Recall"); plt.ylabel("Precision")
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(os.path.join(EVAL_DIR, "precision_recall_curve.png"))
    plt.close()

print("📊 All charts saved to:", EVAL_DIR)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------
print("\n✅ Evaluation Complete")
for k,v in metrics.items():
    if isinstance(v,(float,int)): print(f"   {k:<15} = {v:.4f}")

gc.collect()