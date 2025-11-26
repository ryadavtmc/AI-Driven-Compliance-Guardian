# scripts/prepare_ner_dataset.py
import os, json
from tqdm import tqdm

RAW_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/ner"
PROC_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/ner"
os.makedirs(PROC_DIR, exist_ok=True)

def normalize(jsonl_path, out_path):
    out = []
    with open(jsonl_path, "r") as f:
        for line in tqdm(f, desc=f"Processing {jsonl_path}"):
            ex = json.loads(line)

            # pick correct text field
            text = ex.get("source_text") or ex.get("text") or ex.get("masked_text")

            # pick entities
            spans = ex.get("privacy_mask") or ex.get("spans") or []

            norm_spans = []
            for s in spans:
                try:
                    norm_spans.append({
                        "start": int(s["start"]),
                        "end": int(s["end"]),
                        "label": str(s.get("label") or "PII")
                    })
                except Exception as e:
                    print("⚠️ bad span:", s, e)

            out.append({"text": text, "spans": norm_spans})

    with open(out_path, "w") as f:
        for ex in out:
            f.write(json.dumps(ex) + "\n")

    print(f"✅ Wrote {len(out)} examples to {out_path}")

normalize(os.path.join(RAW_DIR, "train.jsonl"), os.path.join(PROC_DIR, "train.jsonl"))
normalize(os.path.join(RAW_DIR, "validation.jsonl"), os.path.join(PROC_DIR, "validation.jsonl"))