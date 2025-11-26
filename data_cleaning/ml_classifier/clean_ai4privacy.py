import os
import json
from datasets import load_dataset
from tqdm import tqdm

# Paths
RAW_CACHE = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/ml_classifier/huggingface/ai4privacy"
PROC_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/ml_classifier/pii-masking"
os.makedirs(PROC_DIR, exist_ok=True)

def main():
    # Load dataset from Hugging Face
    ds = load_dataset("ai4privacy/pii-masking-300k", cache_dir=RAW_CACHE)

    out_path = os.path.join(PROC_DIR, "pii_masking_clean.jsonl")
    count = 0

    with open(out_path, "w") as fout:
        for split in ["train", "validation"]:
            if split not in ds:
                continue

            for ex in tqdm(ds[split], desc=f"Processing {split}"):
                # Use the source_text field
                text = ex.get("source_text") or ""
                text = text.strip()

                # Skip very short texts
                if len(text.split()) < 5:
                    continue

                # Keep only text + label
                rec = {
                    "text": text,
                    "label": "unsafe"   # all samples are unsafe
                }
                fout.write(json.dumps(rec) + "\n")
                count += 1

    print(f"✅ Wrote {count} records to {out_path}")

if __name__ == "__main__":
    main()
