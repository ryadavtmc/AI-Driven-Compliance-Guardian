"""
Training script for Model 1: NER PII/PHI Detector
-------------------------------------------------
Supports:
  (A) token-level: {"tokens", "ner_tags"}
  (B) span-level: {"text", "spans" | "entities" | "label"}

Example (local JSONL):
  python scripts/train_ner.py \
    --data_dir data/processed/ner \
    --model_name distilbert-base-uncased \
    --output_dir models/pii_ner_distilbert \
    --epochs 2 --batch_size 8
"""

import argparse
import os
import numpy as np
from typing import List, Dict, Any
from datasets import load_dataset, DatasetDict, ClassLabel
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
    TrainingArguments,
    Trainer,
)
from seqeval.metrics import precision_score, recall_score, f1_score


# ----------------------------
# Argument parsing
# ----------------------------
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=str, default=None)
    ap.add_argument("--subset", type=str, default=None)
    ap.add_argument("--data_dir", type=str, default=None)
    ap.add_argument("--model_name", type=str, default="distilbert-base-uncased")
    ap.add_argument("--output_dir", type=str, default="models/pii_ner_distilbert")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch_size", type=int, default=8)
    ap.add_argument("--learning_rate", type=float, default=5e-5)
    ap.add_argument("--weight_decay", type=float, default=0.01)
    ap.add_argument("--max_train_samples", type=int, default=0)
    ap.add_argument("--max_eval_samples", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()


# ----------------------------
# Schema detection
# ----------------------------
def detect_schema(example: Dict[str, Any]) -> str:
    if "tokens" in example and "ner_tags" in example:
        return "token"
    if "text" in example and any(k in example for k in ("spans", "entities", "label")):
        return "span"
    raise ValueError(f"Unsupported dataset schema: {list(example.keys())}")


# ----------------------------
# Token schema alignment
# ----------------------------
def align_token_schema(batch, tokenizer, label_names: List[str]):
    tokenized = tokenizer(
        batch["tokens"], is_split_into_words=True, truncation=True, padding=True
    )
    aligned_labels = []
    for i in range(len(batch["tokens"])):
        word_ids = tokenized.word_ids(i)
        labels = batch["ner_tags"][i]
        label_ids = []
        prev = None
        for wid in word_ids:
            if wid is None:
                label_ids.append(-100)
            elif wid != prev:
                label_ids.append(labels[wid])
            else:
                label_ids.append(labels[wid])
            prev = wid
        aligned_labels.append(label_ids)
    tokenized["labels"] = aligned_labels
    return tokenized


# ----------------------------
# Span schema alignment
# ----------------------------
def align_span_schema(batch, tokenizer, label_list: List[str]):
    texts = batch["text"]

    # ensure list[str]
    texts = ["" if t is None else str(t) for t in texts]

    tokenized = tokenizer(
        texts,
        truncation=True,
        padding="max_length",
        max_length=128,
        return_offsets_mapping=True,
    )

    all_labels = []
    for i, offsets in enumerate(tokenized["offset_mapping"]):
        labels = ["O"] * len(offsets)
        spans = batch["spans"][i] if "spans" in batch and batch["spans"][i] else []
        for span in spans:
            start, end, lbl = span["start"], span["end"], span["label"]
            for j, (tok_start, tok_end) in enumerate(offsets):
                if tok_start >= start and tok_end <= end and tok_start < tok_end:
                    labels[j] = f"B-{lbl}" if labels[j] == "O" else f"I-{lbl}"
        all_labels.append(
            [label_list.index(l) if l in label_list else 0 for l in labels]
        )
    tokenized["labels"] = all_labels
    tokenized.pop("offset_mapping")
    return tokenized


# ----------------------------
# Metrics
# ----------------------------
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    true_preds, true_labels = [], []
    for p_row, l_row in zip(preds, labels):
        cur_p, cur_l = [], []
        for p, l in zip(p_row, l_row):
            if l != -100:
                cur_p.append(p)
                cur_l.append(l)
        true_preds.append(cur_p)
        true_labels.append(cur_l)

    return {
        "precision": precision_score(true_labels, true_preds),
        "recall": recall_score(true_labels, true_preds),
        "f1": f1_score(true_labels, true_preds),
    }


# ----------------------------
# Dataset loader
# ----------------------------
def _load_dataset(args) -> DatasetDict:
    if args.data_dir:
        tpath = os.path.join(args.data_dir, "train.jsonl")
        vpath = os.path.join(args.data_dir, "validation.jsonl")
        ds = load_dataset("json", data_files={"train": tpath, "validation": vpath})
        return DatasetDict(train=ds["train"], test=ds["validation"])
    if args.dataset:
        ds = (
            load_dataset(args.dataset, args.subset)
            if args.subset
            else load_dataset(args.dataset)
        )
        if "train" in ds and "test" in ds:
            return DatasetDict(train=ds["train"], test=ds["test"])
        if "validation" in ds:
            return DatasetDict(train=ds["train"], test=ds["validation"])
        tmp = ds["train"].train_test_split(test_size=0.1, seed=args.seed)
        return DatasetDict(train=tmp["train"], test=tmp["test"])
    raise ValueError("Provide --data_dir or --dataset")


# ----------------------------
# Main
# ----------------------------
def main():
    args = parse_args()
    ds = _load_dataset(args)

    train_split, eval_split = ds["train"], ds["test"]
    schema = detect_schema(train_split[0])
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    # Build label list
    label_list = ["O"]
    if schema == "token":
        feat = train_split.features.get("ner_tags")
        if hasattr(feat, "feature") and isinstance(feat.feature, ClassLabel):
            label_list = feat.feature.names
        else:
            uniq = set()
            for ex in train_split.select(range(min(2000, len(train_split)))):
                for t in ex["ner_tags"]:
                    uniq.update(t if isinstance(t, list) else [t])
            label_list = ["O"] + sorted(list(uniq - {"O"}))

        def enc(batch):
            return align_token_schema(batch, tokenizer, label_list)

    else:  # span schema
        # Collect labels from spans
        uniq = set()
        for ex in train_split.select(range(min(2000, len(train_split)))):
            for s in ex.get("spans", []):
                uniq.add(s["label"])
        label_list = (
            ["O"] + [f"B-{l}" for l in sorted(uniq)] + [f"I-{l}" for l in sorted(uniq)]
        )

        def enc(batch):
            return align_span_schema(batch, tokenizer, label_list)

    if args.max_train_samples:
        train_split = train_split.select(
            range(min(args.max_train_samples, len(train_split)))
        )
    if args.max_eval_samples:
        eval_split = eval_split.select(
            range(min(args.max_eval_samples, len(eval_split)))
        )

    train_tok = train_split.map(
        enc, batched=True, remove_columns=train_split.column_names
    )
    eval_tok = eval_split.map(enc, batched=True, remove_columns=eval_split.column_names)

    id2label = {i: l for i, l in enumerate(label_list)}
    label2id = {l: i for i, l in enumerate(label_list)}

    model = AutoModelForTokenClassification.from_pretrained(
        args.model_name,
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id,
    )

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        eval_strategy="epoch",  # fixed
        save_strategy="epoch",
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        logging_steps=50,
        seed=args.seed,
        report_to="none",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        remove_unused_columns=False,  # critical fix
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tok,
        eval_dataset=eval_tok,
        tokenizer=tokenizer,
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("Saved model to:", args.output_dir)
    print("Eval metrics:", trainer.evaluate())


if __name__ == "__main__":
    main()


""" 
python3 scripts/train_ner.py \
  --data_dir data/processed/ner/ \
  --model_name distilbert-base-uncased \
  --output_dir models/pii_ner_distilbert \
  --epochs 2 --batch_size 8
"""
