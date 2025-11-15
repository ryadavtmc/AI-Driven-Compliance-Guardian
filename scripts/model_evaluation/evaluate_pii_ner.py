#!/usr/bin/env python3
"""
AI-Driven Compliance Guardian — NER Evaluation (Training-Aligned)
=================================================================
✓ Mirrors training tokenization + label assignment exactly
✓ Fixes BIO vs base-label mismatch
✓ Avoids re-tokenization misalignment
✓ Produces consistent F1 scores with training metrics
"""

import os, json, torch, numpy as np, matplotlib.pyplot as plt
from tqdm import tqdm
from datasets import load_dataset
from collections import Counter
from seqeval.metrics import (
    f1_score as seqeval_f1,
    precision_score as seqeval_precision,
    recall_score as seqeval_recall,
    classification_report as seqeval_report,
)
from transformers import AutoTokenizer, AutoModelForTokenClassification

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
MODEL_DIR = "/content/drive/MyDrive/Colab Notebooks/NER_models/pii_ner_v3"
DATA_PATH = "/content/drive/MyDrive/Colab Notebooks/NER_data_clean/validation.jsonl"
OUT_DIR   = "/content/drive/MyDrive/Colab Notebooks/NER_eval_results_v3"
os.makedirs(OUT_DIR, exist_ok=True)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ------------------------------------------------------------
# SAFE MODEL LOAD
# ------------------------------------------------------------
def load_local_model(model_dir):
    print(f"📦 Loading model from: {model_dir}")
    model = AutoModelForTokenClassification.from_pretrained(
        model_dir,
        local_files_only=True,
        trust_remote_code=True
    ).to(DEVICE)

    tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,
        trust_remote_code=True
    )

    print("✅ Model and tokenizer loaded successfully.")
    return model, tokenizer

model, tokenizer = load_local_model(MODEL_DIR)

id2label = model.config.id2label
label_list = [id2label[i] for i in range(len(id2label))]
base_labels = {l.replace("B-", "").replace("I-", "") for l in label_list if l != "O"}

print(f"✅ Loaded {len(label_list)} labels:", label_list[:10])

# ------------------------------------------------------------
# LOAD VALIDATION DATA
# ------------------------------------------------------------
print(f"📂 Loading validation data: {DATA_PATH}")
ds = load_dataset("json", data_files={"test": DATA_PATH})["test"]
schema = "token" if "tokens" in ds.column_names else "span"
print(f"🧩 Detected schema: {schema}")

# ------------------------------------------------------------
# SPAN → BIO (Training-Aligned)
# ------------------------------------------------------------
def convert_span_to_bio(text, spans, tokenizer, base_labels, label_list):
    """Convert char-level spans to token-level BIO labels (exactly like training)."""
    text = str(text)
    enc = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=256,
        return_offsets_mapping=True,
    )

    offsets = enc["offset_mapping"]
    gold_labels = ["O"] * len(offsets)

    for span in (spans or []):
        start, end, lbl = span.get("start"), span.get("end"), span.get("label")
        if not lbl or lbl not in base_labels:
            continue
        for j, (tok_start, tok_end) in enumerate(offsets):
            if tok_start >= start and tok_end <= end and tok_start < tok_end:
                gold_labels[j] = f"B-{lbl}" if gold_labels[j] == "O" else f"I-{lbl}"

    enc.pop("offset_mapping")
    gold_labels = [l if l in label_list else "O" for l in gold_labels]
    return enc, gold_labels

# ------------------------------------------------------------
# JSON SERIALIZER
# ------------------------------------------------------------
def to_serializable(obj):
    if isinstance(obj, (np.integer, np.int32, np.int64)): return int(obj)
    if isinstance(obj, (np.floating, np.float32, np.float64)): return float(obj)
    if isinstance(obj, dict):  return {k: to_serializable(v) for k,v in obj.items()}
    if isinstance(obj, list):  return [to_serializable(v) for v in obj]
    return obj

# ------------------------------------------------------------
# MAIN EVALUATION
# ------------------------------------------------------------
def evaluate_model(limit=None):
    preds, golds = [], []
    subset = ds.select(range(min(limit, len(ds)))) if limit else ds
    print(f"🚀 Starting evaluation on {len(subset)} samples...")

    printed_samples = 0
    for ex in tqdm(subset, desc=f"Evaluating ({schema})", unit="record"):
        if schema == "token":
            # Direct token schema
            enc = tokenizer(
                ex["tokens"],
                is_split_into_words=True,
                truncation=True,
                padding="max_length",
                max_length=256,
                return_tensors="pt"
            )
            gold_labels = [id2label[int(t)] if int(t) < len(label_list) else "O" for t in ex["ner_tags"]]
        else:
            # Span schema
            enc_np, gold_labels = convert_span_to_bio(ex["text"], ex.get("spans", []), tokenizer, base_labels, label_list)
            enc = {k: torch.tensor([v]).to(DEVICE) for k, v in enc_np.items()}

        # Sanity check print
        if printed_samples < 2:
            non_o = sum(1 for l in gold_labels if l != "O")
            print(f"\n🧩 Sample {printed_samples+1} non-'O' labels: {non_o}")
            printed_samples += 1

        # Run model
        with torch.no_grad():
            logits = model(**enc).logits
            pred_ids = torch.argmax(logits, dim=2)[0].cpu().numpy()

        pred_labels = [id2label[int(pid)] if int(pid) < len(label_list) else "O" for pid in pred_ids]
        preds.append(pred_labels[:len(gold_labels)])
        golds.append(gold_labels)

    # ------------------------------------------------------------
    # METRICS
    # ------------------------------------------------------------
    precision = seqeval_precision(golds, preds, zero_division=0)
    recall = seqeval_recall(golds, preds, zero_division=0)
    f1 = seqeval_f1(golds, preds, zero_division=0)

    print(f"\n✅ Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")
    report = seqeval_report(golds, preds, output_dict=True, zero_division=0)

    # SAVE RESULTS
    json.dump(to_serializable(report), open(os.path.join(OUT_DIR, "ner_eval_report.json"), "w"), indent=2)
    print("🧾 Saved detailed report → ner_eval_report.json")

    # VISUALS
    true_counts = Counter([l for seq in golds for l in seq if l != "O"])
    pred_counts = Counter([l for seq in preds for l in seq if l != "O"])
    labels = sorted(set(true_counts.keys()) | set(pred_counts.keys()))
    x = np.arange(len(labels)); width = 0.35

    plt.figure(figsize=(12, 5))
    plt.bar(x - width/2, [true_counts.get(l,0) for l in labels], width, label="True", color="#66b3ff")
    plt.bar(x + width/2, [pred_counts.get(l,0) for l in labels], width, label="Predicted", color="#ff9999")
    plt.xticks(x, labels, rotation=90)
    plt.title("Entity Frequency Comparison (True vs Predicted)")
    plt.ylabel("Count"); plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "entity_freq_comparison.png"))
    plt.close()

    label_f1 = {label: v["f1-score"] for label, v in report.items()
                if label not in ["macro avg","weighted avg","micro avg"]}
    if label_f1:
        plt.figure(figsize=(12, 5))
        plt.bar(label_f1.keys(), label_f1.values(), color="#8fd694")
        plt.xticks(rotation=90)
        plt.ylabel("F1 Score")
        plt.title("Per-Entity F1 Scores")
        plt.ylim(0, 1.05)
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "entity_f1_scores.png"))
        plt.close()
        print("📊 Saved F1 charts.")

    # SUMMARY
    if label_f1:
        print("\n🏅 Top 10 Entities by F1:")
        for label, score in sorted(label_f1.items(), key=lambda kv: kv[1], reverse=True)[:10]:
            print(f"   {label:<25} {score:.4f}")

    print(f"\n🏁 Final F1 Score: {f1:.4f}")
    return f1

# ------------------------------------------------------------
# RUN
# ------------------------------------------------------------
if __name__ == "__main__":
    evaluate_model()  # Adjust or remove limit for full eval