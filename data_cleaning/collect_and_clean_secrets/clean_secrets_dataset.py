#!/usr/bin/env python3
"""
Dataset Cleaner & Splitter for Secrets
--------------------------------------
1. Loads multiple leaks JSONL files (leaks.jsonl, leak_v2.jsonl, leak_v3.jsonl).
2. Deduplicates leaks by Fingerprint (or fallback File+Rule+Line hash).
3. Tags "LikelyTest" = True if from test/example/demo/docs paths.
4. Splits into:
   - real_secrets.jsonl → LikelyTest == False
   - dummy_secrets.jsonl → LikelyTest == True
   - all_secrets_clean.jsonl → everything merged & deduped
"""

import os
import json
import hashlib
from pathlib import Path

# -------------------
# Config
# -------------------
INPUT_FILES = [
    "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/notebooks/collect_and_create_secrets/leaks.jsonl",
    "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/notebooks/collect_and_create_secrets/leak_v2.jsonl",
    "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/notebooks/collect_and_create_secrets/leak_v3.jsonl"
]

OUTPUT_ALL = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/secrets/all_secrets_clean.jsonl"
OUTPUT_REAL = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/secrets/real_secrets.jsonl"
OUTPUT_DUMMY = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/secrets/dummy_secrets.jsonl"

TEST_KEYWORDS = ["test", "tests", "example", "examples", "demo", "sample", "docs"]

# -------------------
# Utils
# -------------------
def compute_fallback_fp(leak: dict) -> str:
    """Generate fallback fingerprint if Fingerprint missing"""
    base = f"{leak.get('File','')}|{leak.get('RuleID','')}|{leak.get('StartLine','')}"
    return hashlib.sha256(base.encode()).hexdigest()

def tag_likely_test(file_path: str) -> bool:
    """Check if file path suggests test/demo/example"""
    lower_path = file_path.lower()
    return any(kw in lower_path for kw in TEST_KEYWORDS)

# -------------------
# Main
# -------------------
def merge_and_split(input_files):
    seen = set()
    cleaned = []

    for fpath in input_files:
        if not Path(fpath).exists():
            print(f"⚠️ Skipping missing file: {fpath}")
            continue
        print(f"📂 Loading {fpath}...")
        with open(fpath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    leak = json.loads(line)
                except:
                    continue

                # Determine fingerprint
                fp = leak.get("Fingerprint")
                if not fp:
                    fp = compute_fallback_fp(leak)

                # Deduplication
                if fp in seen:
                    continue
                seen.add(fp)

                # Add metadata
                leak["LikelyTest"] = tag_likely_test(leak.get("File", ""))

                cleaned.append(leak)

    print(f"✅ Total unique leaks: {len(cleaned)}")

    # Split datasets
    real = [leak for leak in cleaned if not leak["LikelyTest"]]
    dummy = [leak for leak in cleaned if leak["LikelyTest"]]

    # Save outputs
    def save_jsonl(data, path):
        with open(path, "w") as out:
            for leak in data:
                out.write(json.dumps(leak) + "\n")
        print(f"📦 Saved {len(data)} → {path}")

    save_jsonl(cleaned, OUTPUT_ALL)
    save_jsonl(real, OUTPUT_REAL)
    save_jsonl(dummy, OUTPUT_DUMMY)

if __name__ == "__main__":
    merge_and_split(INPUT_FILES)