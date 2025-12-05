import os
import json
import random
import pandas as pd

# ------------------
# Paths
# ------------------
DATA_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/ml_classifier"
SAFE_FILES = {
    "imdb": os.path.join(DATA_DIR, "safe_datasets/imdb_train.jsonl"),
    "wikipedia": os.path.join(DATA_DIR, "safe_datasets/wikipedia_100k.jsonl"),
    "ag_news": os.path.join(DATA_DIR, "safe_datasets/ag_news_train.jsonl"),
}
OUTPUT_FILE = os.path.join(DATA_DIR, "augmented_safe_unsafe.jsonl")

# ------------------
# Helpers
# ------------------
def load_jsonl(path, limit=None):
    records = []
    with open(path, "r") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            try:
                records.append(json.loads(line))
            except:
                continue
    return pd.DataFrame(records)

def save_jsonl(records, path):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

# ------------------
# 1. Load Safe Data
# ------------------
def load_safe_data():
    dfs = []
    for name, path in SAFE_FILES.items():
        if os.path.exists(path):
            print(f"📂 Loading {name}...")
            dfs.append(load_jsonl(path, limit=20000))  # limit for speed
    df = pd.concat(dfs, ignore_index=True)
    return df

# ------------------
# 2. Filter Keyword-Rich Safe
# ------------------
def filter_keyword_safe(df):
    keywords = ["email", "phone", "number", "contact", "address"]
    mask = df["text"].str.contains("|".join(keywords), case=False, na=False)
    return df[mask].assign(label="safe")

# ------------------
# 3. Generate Synthetic Unsafe
# ------------------
def generate_unsafe_samples(n=5000):
    unsafe_patterns = [
        "John Doe SSN: 123-45-6789",
        "Credit Card: 4111-1111-1111-1111",
        "Phone: 555-123-4567",
        "Email: test@example.com",
        "Bank account: 123456789",
    ]
    samples = []
    for _ in range(n):
        text = random.choice(unsafe_patterns)
        samples.append({"text": text, "label": "unsafe"})
    return pd.DataFrame(samples)

# ------------------
# Main
# ------------------
def main():
    print("📂 Loading safe data...")
    safe_df = load_safe_data()

    print("🔎 Filtering keyword-rich safe samples...")
    keyword_safe = filter_keyword_safe(safe_df)

    print("⚡ Generating synthetic unsafe samples...")
    unsafe_df = generate_unsafe_samples(n=len(keyword_safe))

    print("🤝 Balancing datasets...")
    augmented = pd.concat([keyword_safe, unsafe_df], ignore_index=True)
    print("✅ Final size:", len(augmented))
    print("Class distribution:\n", augmented["label"].value_counts())

    print(f"💾 Saving to {OUTPUT_FILE}...")
    save_jsonl(augmented.to_dict(orient="records"), OUTPUT_FILE)
    print("🎉 Augmented dataset saved!")

if __name__ == "__main__":
    main()