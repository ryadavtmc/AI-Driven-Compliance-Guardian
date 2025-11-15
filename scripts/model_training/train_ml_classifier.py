
#!/usr/bin/env python3
#!/usr/bin/env python3
"""
ML Classifier (Hybrid — Bias-Corrected + RF-Weighted + PII-Aware)
-----------------------------------------------------------------
Enhancements:
  ✅ Length & token density normalization
  ✅ PII regex patterns (SSN, credit card, email, phone, API key, JWT)
  ✅ Amplified numeric signals for stronger RandomForest sensitivity
  ✅ Smarter ensemble weighting (RF prioritized)
  ✅ Bias-corrected calibration & validation tuning
"""

import os, json, math, re, time, gc, multiprocessing, joblib, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from tqdm import tqdm
from imblearn.over_sampling import RandomOverSampler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, f1_score, brier_score_loss, log_loss
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from scipy.sparse import csr_matrix, hstack, vstack

from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.calibration import CalibratedClassifierCV
from xgboost import XGBClassifier

import seaborn as sns
import matplotlib.pyplot as plt

# Optional memory stats
try:
    import psutil
    HAVE_PSUTIL = True
except Exception:
    HAVE_PSUTIL = False

# -------------------
# Paths
# -------------------
BASE_DIR  = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/ml_classifier"
MODEL_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/models/ml_classifier"
os.makedirs(MODEL_DIR, exist_ok=True)

FILES = {
    "sec_filings":     os.path.join(BASE_DIR, "sec-edgar-filings/sec_filings_all.jsonl"),
    "pii_masking":     os.path.join(BASE_DIR, "pii-masking/pii_masking.jsonl"),
    "synthetic_pii":   os.path.join(BASE_DIR, "synthetic_data_pii/train_classifier.jsonl"),
    "ag_news":         os.path.join(BASE_DIR, "safe_datasets/ag_news_train.jsonl"),
    "imdb":            os.path.join(BASE_DIR, "safe_datasets/imdb_train.jsonl"),
    "wikipedia":       os.path.join(BASE_DIR, "safe_datasets/wikipedia_100k.jsonl"),
    "augmented":       os.path.join(BASE_DIR, "augmented_safe_unsafe.jsonl"),
    "faker_generated": os.path.join(BASE_DIR, "faker_augmented.jsonl"),
}

CPU_CORES = multiprocessing.cpu_count()
RNG = 42

# -------------------
# Config
# -------------------
TFIDF_MAX_FEATURES = 50_000
TFIDF_BATCH        = 60_000
STOPWORDS          = "english"
MIN_DF             = 2
DTYPE              = np.float32

# -------------------
# Helpers
# -------------------
def log_mem(prefix="💾"):
    if not HAVE_PSUTIL: return
    mem = psutil.virtual_memory()
    print(f"{prefix} Memory: {mem.used/1e9:.2f} GB / {mem.total/1e9:.1f} GB ({mem.percent}%)")

def entropy(s: str) -> float:
    if not s: return 0.0
    p = [s.count(c) / len(s) for c in set(s)]
    return -sum(pi * math.log(pi, 2) for pi in p)

def numeric_features(texts):
    """Generate robust PII-aware numeric features with amplification."""
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

        # PII pattern flags
        looks_jwt   = bool(re.search(r"eyJ[a-zA-Z0-9_-]{10,}\.", t))
        looks_key   = bool(re.search(r"(sk_|gh[pousr]_)", t))
        looks_ssn   = bool(re.search(r"\b\d{3}-\d{2}-\d{4}\b", t))
        looks_cc    = bool(re.search(r"\b(?:\d[ -]*?){13,16}\b", t))
        looks_email = bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", t))
        looks_phone = bool(re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", t))

        # amplified signals ×5
        rows.append([
            num_chars / 500.0, num_words / 100.0, avg_word_len / 10.0,
            token_density, entropy_val, digit_density, symbol_density,
            5*int(looks_jwt), 5*int(looks_key), 5*int(looks_ssn),
            5*int(looks_cc), 5*int(looks_email), 5*int(looks_phone)
        ])
    X = np.asarray(rows, dtype=DTYPE)
    return X * 10.0  # global amplification

def load_jsonl(path):
    data = []
    with open(path, "r") as f:
        for line in f:
            try: data.append(json.loads(line))
            except: continue
    return pd.DataFrame(data)

def load_all_datasets():
    dfs = []
    print("📂 Loading datasets...")
    for name, path in FILES.items():
        if os.path.exists(path):
            df = load_jsonl(path)
            print(f"   ✅ {name:<20} → {len(df):>7,} rows")
            dfs.append(df)
        else:
            print(f"   ⚠️ Missing {path}")
    return pd.concat(dfs, ignore_index=True)

# -------------------
# TF-IDF building
# -------------------
tfidf_vectorizer = TfidfVectorizer(
    max_features=TFIDF_MAX_FEATURES,
    ngram_range=(1, 2),
    stop_words=STOPWORDS,
    min_df=MIN_DF,
    dtype=DTYPE,
    lowercase=True,
    strip_accents="unicode"
)

def fit_tfidf_batched(vectorizer, texts, batch_size=TFIDF_BATCH):
    texts = np.asarray(texts, dtype=object)
    n = len(texts)
    batches = [(i, min(i+batch_size, n)) for i in range(0, n, batch_size)]
    print(f"⚙️  TF-IDF in {len(batches)} batches (batch={batch_size}, cores={CPU_CORES})")
    lo, hi = batches[0]
    t0 = time.time()
    tfidf = vectorizer.fit_transform(texts[lo:hi])
    print(f"   ✅ Batch 1 fit: {lo}-{hi} | shape={tfidf.shape}")
    parts = joblib.Parallel(n_jobs=CPU_CORES)(
        joblib.delayed(vectorizer.transform)(texts[lo:hi]) for lo,hi in tqdm(batches[1:], desc="🧠 TF-IDF transforming")
    )
    if parts: tfidf = vstack([tfidf]+parts, format="csr")
    print(f"✅ TF-IDF built in {time.time()-t0:.1f}s | shape={tfidf.shape}")
    log_mem("📊")
    return tfidf

def build_features(train_texts, test_texts):
    print("\n🔎 Extracting TF-IDF + numeric features...")
    tfidf_train = fit_tfidf_batched(tfidf_vectorizer, train_texts)
    tfidf_test  = tfidf_vectorizer.transform(tqdm(test_texts, desc="🧩 TF-IDF (test)"))
    num_train, num_test = numeric_features(train_texts), numeric_features(test_texts)
    print(f"📐 Numeric features shape: {num_train.shape}")

    scaler = StandardScaler(with_mean=False)
    num_train_scaled = scaler.fit_transform(num_train)
    num_test_scaled  = scaler.transform(num_test)

    X_train = hstack([tfidf_train, csr_matrix(num_train_scaled)], format="csr")
    X_test  = hstack([tfidf_test,  csr_matrix(num_test_scaled)],  format="csr")
    gc.collect()
    print(f"✅ Combined features: Train {X_train.shape}, Test {X_test.shape}")
    return X_train, X_test

# -------------------
# Models
# -------------------
def build_models():
    lr  = LogisticRegression(max_iter=500, class_weight="balanced", solver="saga", n_jobs=-1, random_state=RNG)
    rf  = RandomForestClassifier(n_estimators=160, max_depth=16, class_weight="balanced", n_jobs=-1, random_state=RNG)
    xgb = XGBClassifier(
        n_estimators=250, max_depth=7, learning_rate=0.1,
        subsample=0.85, colsample_bytree=0.9, n_jobs=-1,
        tree_method="hist", eval_metric="logloss", random_state=RNG
    )
    svm = LinearSVC(class_weight="balanced", max_iter=3000, random_state=RNG)
    nb  = MultinomialNB()

    lr_cal   = CalibratedClassifierCV(lr,  method="sigmoid",  cv=3)
    rf_cal   = rf  # RF already well-calibrated
    xgb_cal  = CalibratedClassifierCV(xgb, method="sigmoid",  cv=3)
    svm_cal  = CalibratedClassifierCV(svm, method="sigmoid",  cv=3)
    nb_cal   = nb  # NB already probabilistic

    return lr_cal, rf_cal, xgb_cal, svm_cal, nb_cal

# -------------------
# Ensemble weight tuning
# -------------------
def tune_weights(models, X_val, y_val):
    candidates = [
        (1.0, 2.0, 0.8, 1.2, 0.8),
        (1.2, 2.0, 0.8, 1.0, 0.8),
        (1.0, 2.5, 0.8, 1.1, 0.7),
        (0.8, 2.0, 0.7, 1.2, 0.8)
    ]
    order = ["logreg","random_forest","xgboost","svm","naive_bayes"]
    probas = {n: models[n].predict_proba(X_val) for n in order}
    best = None
    for w in candidates:
        W = np.array(w)
        P = sum(W[i]*probas[n] for i,n in enumerate(order)) / W.sum()
        y_hat = (P[:,1] >= 0.5).astype(int)
        f1 = f1_score(y_val, y_hat, average="macro")
        brier = brier_score_loss(y_val, P[:,1])
        if (best is None) or ((f1, -brier) > best[0]): best = ((f1, -brier), w)
    print(f"🎯 Best weights (LR,RF,XGB,SVM,NB): {best[1]}")
    return best[1]

# -------------------
# Main
# -------------------
def main():
    print(f"🧠 Using {CPU_CORES} cores"); log_mem("🚦")
    t0 = time.time()

    df = load_all_datasets().dropna(subset=["text","label"])
    print(f"\n✅ Clean dataset: {len(df):,}")
    print(df["label"].value_counts(), "\n")

    le = LabelEncoder()
    df["y"] = le.fit_transform(df["label"])
    assert set(le.classes_) == {"safe","unsafe"}
    print("🔖 Label map:", dict(zip(le.classes_, le.transform(le.classes_))))

    # Length-aware oversampling
    df["len_bin"] = pd.qcut(df["text"].str.len(), q=4, labels=False, duplicates="drop")
    ros = RandomOverSampler(random_state=RNG)
    X_res_df, y_res = ros.fit_resample(df[["text","len_bin"]], df["y"])
    X_res_df = X_res_df.drop(columns="len_bin")
    print(f"✅ Oversampled total: {len(X_res_df):,}")

    X_train_texts, X_test_texts, y_train, y_test = train_test_split(
        X_res_df["text"].astype(str), y_res, test_size=0.2, random_state=RNG, stratify=y_res
    )
    print(f"✂️ Train: {len(X_train_texts):,}, Test: {len(X_test_texts):,}")

    X_train, X_test = build_features(X_train_texts, X_test_texts)
    X_tr, X_val, y_tr, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=RNG, stratify=y_train)
    print(f"   ↳ Inner split → train_inner={X_tr.shape[0]:,}, val={X_val.shape[0]:,}")

    # Train base models
    lr_cal, rf_cal, xgb_cal, svm_cal, nb_cal = build_models()
    models = {
        "logreg": lr_cal, "random_forest": rf_cal, "xgboost": xgb_cal,
        "svm": svm_cal, "naive_bayes": nb_cal
    }
    for n,m in models.items():
        print(f"⚙️  Training {n} ...")
        m.fit(X_tr, y_tr)
        print(f"✅ {n} trained")

    best_weights = tune_weights(models, X_val, y_val)

    # Refit full models on entire training data
    for n,m in models.items():
        print(f"🔁 Re-fitting {n} on full train ...")
        m.fit(X_train, y_train)

    ensemble = VotingClassifier(
        estimators=list(models.items()),
        voting="soft",
        weights=list(best_weights),
        n_jobs=-1
    )
    print("⚙️  Fitting final ensemble ...")
    ensemble.fit(X_train, y_train)
    print(f"✅ Ensemble fitted | weights={best_weights}")

    # Save all artifacts
    for n,m in models.items():
        joblib.dump(m, os.path.join(MODEL_DIR, f"{n}.pkl"))
    joblib.dump(ensemble, os.path.join(MODEL_DIR, "ensemble.pkl"))
    joblib.dump(tfidf_vectorizer, os.path.join(MODEL_DIR, "tfidf.pkl"))
    joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.pkl"))
    print("💾 Models saved →", MODEL_DIR)

    # Evaluation
    print("\n📊 Evaluating on test...")
    y_pred = ensemble.predict(X_test)
    print(classification_report(y_test, y_pred, digits=4, target_names=["safe","unsafe"]))
    cm = confusion_matrix(y_test, y_pred, labels=[0,1])
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["safe","unsafe"], yticklabels=["safe","unsafe"])
    plt.title("Confusion Matrix — Hybrid RF-Weighted Model")
    plt.xlabel("Predicted"); plt.ylabel("True")
    plt.show()

    print(f"\n🏁 Done in {time.time()-t0:.1f}s total."); log_mem("🧩")

if __name__ == "__main__":
    main()