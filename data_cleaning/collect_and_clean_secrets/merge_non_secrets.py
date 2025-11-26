#!/usr/bin/env python3
"""
Non-Secrets Merger & Cleaner
----------------------------
1. Reads multiple non_secrets.jsonl files (large-safe, streaming).
2. Deduplicates by ("text","file","repo").
3. Filters out lines that are too short/long or junk.
4. Normalizes structure (keeps only needed fields).
5. Writes merged_non_secrets.jsonl (ready for sampling/training).
"""

import json
import hashlib
from pathlib import Path
from tqdm import tqdm

# -------------------
# Config
# -------------------
BASE_DIR = Path("/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/notebooks/collect_and_create_secrets/")

INPUT_FILES = [
    BASE_DIR / "non_secrets.jsonl",
    BASE_DIR / "non_secrets_v2.jsonl",
    BASE_DIR / "non_secrets_v3.jsonl",
    Path("/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/secrets/synthetic_non_secrets.jsonl"),  # synthetic dataset
]

OUTPUT_FILE = BASE_DIR / "merged_non_secrets.jsonl"

# -------------------
# Helpers
# -------------------
def compute_fingerprint(obj):
    """Unique fingerprint by text+file+repo (fallback to text only)."""
    base = f"{obj.get('text','')}|{obj.get('file','')}|{obj.get('repo','')}"
    return hashlib.sha256(base.encode()).hexdigest()

def is_valid(entry):
    """Filter invalid or junk entries."""
    text = str(entry.get("text", "")).strip()
    if not text:
        return False
    if len(text) < 2 or len(text) > 800:
        return False
    # repetitive junk like =====, ----
    if len(set(text)) < 3:
        return False
    return True

def normalize(entry):
    """Keep only fields we need for ML."""
    return {
        "text": str(entry.get("text", "")).strip(),
        "label": int(entry.get("label", 0)),  # default to non-secret
    }

# -------------------
# Main
# -------------------
def merge_non_secrets(input_files, output_file):
    seen = set()
    total_loaded = 0
    total_written = 0

    with open(output_file, "w") as out:
        for fpath in input_files:
            if not Path(fpath).exists():
                print(f"⚠️ Skipping missing file: {fpath}")
                continue

            print(f"📂 Processing {fpath}...")
            with open(fpath, "r") as f:
                for line in tqdm(f, desc=f"Scanning {fpath.name}"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    total_loaded += 1
                    if not is_valid(obj):
                        continue

                    fp = compute_fingerprint(obj)
                    if fp in seen:
                        continue
                    seen.add(fp)

                    obj = normalize(obj)
                    out.write(json.dumps(obj) + "\n")
                    total_written += 1

    print(f"\n📊 Total lines scanned: {total_loaded}")
    print(f"✅ Unique valid non-secrets written: {total_written}")
    print(f"📦 Final merged dataset → {output_file}")

if __name__ == "__main__":
    merge_non_secrets(INPUT_FILES, OUTPUT_FILE)