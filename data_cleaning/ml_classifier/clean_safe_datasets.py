import os
import json
from datasets import load_dataset
from tqdm import tqdm

# -------------------
# Paths
# -------------------
PROC_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/ml_classifier/safe_datasets"
os.makedirs(PROC_DIR, exist_ok=True)

def save_to_jsonl(dataset, out_file, split_name):
    """Save Hugging Face dataset to JSONL format with label=safe."""
    with open(out_file, "w") as fout:
        for i, ex in tqdm(enumerate(dataset), total=len(dataset), desc=f"Processing {split_name}"):
            # Clean text
            text = ex.get("text") or ex.get("content") or ex.get("article") or ex.get("document") or None
            if not text:
                continue
            text = str(text).strip()
            if len(text.split()) < 5:  # skip short
                continue

            record = {
                "id": f"{split_name}_{i}",
                "text": text,
                "label": "safe"
            }
            fout.write(json.dumps(record) + "\n")

    print(f"✅ Saved {split_name} -> {out_file}")


def main():
    # --------------------
    # AG News
    # --------------------
    ds_ag = load_dataset("ag_news")
    for split in ["train", "test"]:
        out_file = os.path.join(PROC_DIR, f"ag_news_{split}.jsonl")
        save_to_jsonl(ds_ag[split], out_file, f"ag_news_{split}")

    # --------------------
    # IMDb
    # --------------------
    ds_imdb = load_dataset("imdb")
    for split in ["train", "test"]:
        out_file = os.path.join(PROC_DIR, f"imdb_{split}.jsonl")
        save_to_jsonl(ds_imdb[split], out_file, f"imdb_{split}")

    # --------------------
    # Wikipedia (first 100k)
    # --------------------
    ds_wiki = load_dataset("wikimedia/wikipedia", "20231101.en", split="train[:100000]")
    out_file = os.path.join(PROC_DIR, f"wikipedia_100k.jsonl")
    save_to_jsonl(ds_wiki, out_file, "wikipedia_100k")


if __name__ == "__main__":
    main()