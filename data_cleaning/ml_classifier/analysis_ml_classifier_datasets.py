import os
import json
import pandas as pd
import psutil
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from tqdm import tqdm

# ------------------
# Paths
# ------------------
DATA_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/ml_classifier"

FILES = {
    "pii_masking": os.path.join(DATA_DIR, "pii-masking/pii_masking.jsonl"),
    "synthetic_pii": os.path.join(DATA_DIR, "synthetic_data_pii/train.jsonl"),
    "sec_filings": os.path.join(DATA_DIR, "sec_filings_all.jsonl"),
    "ag_news_train": os.path.join(DATA_DIR, "safe_datasets/ag_news_train.jsonl"),
    "imdb_train": os.path.join(DATA_DIR, "safe_datasets/imdb_train.jsonl"),
    "wikipedia": os.path.join(DATA_DIR, "safe_datasets/wikipedia_100k.jsonl"),
}

# ------------------
# Helpers
# ------------------
def load_jsonl(path, label_override=None):
    records = []
    with open(path, "r") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if label_override:
                    obj["label"] = label_override
                records.append(obj)
            except:
                continue
    return pd.DataFrame(records)

def top_tfidf_features(X, y, vectorizer, label, n=20):
    clf = LogisticRegression(max_iter=200, class_weight="balanced", n_jobs=-1)
    clf.fit(X, y)
    coef = clf.coef_[0]
    feature_names = vectorizer.get_feature_names_out()
    if label == "safe":
        topn = coef.argsort()[:n]
    else:
        topn = coef.argsort()[-n:]
    return [(feature_names[i], round(float(coef[i]), 4)) for i in topn]

def memory_usage():
    mem = psutil.virtual_memory()
    return f"{mem.used/1e9:.2f} GB / {mem.total/1e9:.2f} GB used"

# ------------------
# Main analysis
# ------------------
def main():
    dfs = {}
    for name, path in FILES.items():
        if os.path.exists(path):
            dfs[name] = load_jsonl(path)

    # 1. Class balance
    all_counts = {}
    for name, df in dfs.items():
        counts = df["label"].value_counts()
        print(f"\n📊 Dataset: {name}\n{counts}")
        all_counts[name] = counts

    # Plot class balance
    balance_df = pd.DataFrame(all_counts).fillna(0).T
    balance_df.plot(kind="bar", stacked=True, figsize=(10,6), colormap="tab20")
    plt.title("Class Balance per Dataset")
    plt.ylabel("Count")
    plt.xlabel("Dataset")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    # 2. Merge for TF-IDF feature analysis (sample for speed)
    merged = pd.concat(dfs.values(), ignore_index=True)
    print("\n✅ Merged dataset size:", len(merged))
    print("Class distribution:\n", merged["label"].value_counts())

    if len(merged) > 50000:
        merged = merged.sample(50000, random_state=42)

    # 3. Sample texts
    print("\n🔎 Example SAFE text:\n", merged[merged["label"]=="safe"]["text"].sample(1).iloc[0][:300])
    print("\n🔎 Example UNSAFE text:\n", merged[merged["label"]=="unsafe"]["text"].sample(1).iloc[0][:300])

    # 4. TF-IDF feature inspection
    print("\n🔎 TF-IDF Feature Analysis...")
    vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1,2))
    X = vectorizer.fit_transform(tqdm(merged["text"], desc="Vectorizing"))
    y = merged["label"]
    print(f"✅ TF-IDF matrix: {X.shape}, RAM usage: {memory_usage()}")

    safe_feats = top_tfidf_features(X, y, vectorizer, "safe", n=20)
    unsafe_feats = top_tfidf_features(X, y, vectorizer, "unsafe", n=20)

    print("\nTop SAFE features:", safe_feats)
    print("\nTop UNSAFE features:", unsafe_feats)

    # Plot top features
    fig, axes = plt.subplots(1, 2, figsize=(14,6))
    sns.barplot(x=[w for _,w in safe_feats], y=[f for f,_ in safe_feats], ax=axes[0], color="skyblue")
    axes[0].set_title("Top SAFE Features")
    sns.barplot(x=[w for _,w in unsafe_feats], y=[f for f,_ in unsafe_feats], ax=axes[1], color="salmon")
    axes[1].set_title("Top UNSAFE Features")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()