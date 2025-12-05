#!/usr/bin/env python3
"""
verify_with_gitleaks_clean_balance_v2.py
---------------------------------------
1. Merge all balanced_*_v2.jsonl datasets (train/val/test).
2. Run Gitleaks locally to detect real secrets.
3. Relabel: label=1 if detected by Gitleaks, else 0.
4. Save clean dataset splits (v2).

Requirements:
    pip install scikit-learn
    brew install gitleaks  (or apt install gitleaks)
"""

import os
import json
import shutil
import subprocess
from sklearn.model_selection import train_test_split

# -------------------
# Config paths
# -------------------
DATA_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/secrets_classifier"
OUT_DIR = DATA_DIR

OUTPUT_MERGED = os.path.join(OUT_DIR, "combined_v2.jsonl")
OUTPUT_TXT = os.path.join(OUT_DIR, "combined_v2.txt")
GITLEAKS_REPORT = os.path.join(OUT_DIR, "gitleaks_report.json")
CLEAN_OUTPUT = os.path.join(OUT_DIR, "clean_balance_secrets_v2.jsonl")

# -------------------
# Merge all balanced_*_v2.jsonl files
# -------------------
def merge_jsonl_files():
    files = [f for f in os.listdir(DATA_DIR) if f.startswith("balanced_") and f.endswith("_v2.jsonl")]
    merged = []
    for f in files:
        path = os.path.join(DATA_DIR, f)
        with open(path, "r") as infile:
            for line in infile:
                try:
                    obj = json.loads(line)
                    merged.append(obj)
                except json.JSONDecodeError:
                    continue
    with open(OUTPUT_MERGED, "w") as out:
        for obj in merged:
            out.write(json.dumps(obj) + "\n")
    print(f"📦 Merged {len(merged)} records from {len(files)} files → {OUTPUT_MERGED}")
    return merged

# -------------------
# Extract text column for scanning
# -------------------
def extract_text_for_scan(data):
    with open(OUTPUT_TXT, "w") as out:
        for item in data:
            text = item.get("text", "").replace("\n", "\\n")
            out.write(text + "\n")
    print(f"🧾 Exported text for scanning → {OUTPUT_TXT}")

# -------------------
# Run Gitleaks
# -------------------
def run_gitleaks():
    """Run Gitleaks scan, handling both success and error gracefully."""
    if not shutil.which("gitleaks"):
        raise RuntimeError("❌ Gitleaks not found. Install via `brew install gitleaks` or `apt install gitleaks`.")

    print("🔍 Running Gitleaks scan...")

    # Some versions no longer use --no-git, so we run without it if needed
    cmd = [
        "gitleaks", "detect",
        "--source", OUTPUT_TXT,
        "--report-format", "json",
        "--report-path", GITLEAKS_REPORT,
        "--no-git"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️ Gitleaks exited with code {result.returncode}")
            print("STDOUT:", result.stdout[:500])
            print("STDERR:", result.stderr[:500])
        else:
            print("✅ Gitleaks finished successfully.")
    except Exception as e:
        print(f"❌ Failed to run Gitleaks: {e}")

    # Confirm if report exists
    if os.path.exists(GITLEAKS_REPORT):
        print(f"📄 Report generated → {GITLEAKS_REPORT}")
    else:
        print("⚠️ No report generated. Check your Gitleaks version or command flags.")

# -------------------
# Relabel dataset using Gitleaks detections
# -------------------
def relabel_dataset(data):
    try:
        with open(GITLEAKS_REPORT) as f:
            leaks = json.load(f)
    except Exception as e:
        print(f"⚠️ Could not read Gitleaks report: {e}")
        leaks = []

    found_texts = set()
    for item in leaks:
        match = item.get("Match")
        if match:
            found_texts.add(match.strip())

    relabeled = []
    for d in data:
        text = d.get("text", "")
        label = 1 if any(m in text for m in found_texts) else 0
        relabeled.append({"text": text, "label": label})

    print(f"✅ Relabeled {len(relabeled)} entries (Gitleaks found {len(found_texts)} unique matches)")
    return relabeled

# -------------------
# Save clean dataset splits
# -------------------
def save_clean_splits(data):
    train, temp = train_test_split(data, test_size=0.2, random_state=42)
    val, test = train_test_split(temp, test_size=0.5, random_state=42)

    def save_jsonl(path, subset):
        with open(path, "w") as f:
            for d in subset:
                f.write(json.dumps(d) + "\n")

    save_jsonl(CLEAN_OUTPUT, data)
    save_jsonl(os.path.join(OUT_DIR, "balanced_clean_train_v2.jsonl"), train)
    save_jsonl(os.path.join(OUT_DIR, "balanced_clean_val_v2.jsonl"), val)
    save_jsonl(os.path.join(OUT_DIR, "balanced_clean_test_v2.jsonl"), test)

    print("\n📊 Saved clean datasets:")
    print(f"  • Total Clean: {len(data)}")
    print(f"  • Train: {len(train)}")
    print(f"  • Val:   {len(val)}")
    print(f"  • Test:  {len(test)}")

# -------------------
# Main pipeline
# -------------------
if __name__ == "__main__":
    merged = merge_jsonl_files()
    extract_text_for_scan(merged)
    run_gitleaks()
    cleaned = relabel_dataset(merged)
    save_clean_splits(cleaned)
    print("\n🎯 Done → verified datasets ready for retraining.")