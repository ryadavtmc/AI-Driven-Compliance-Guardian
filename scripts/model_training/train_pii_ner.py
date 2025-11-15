#!/usr/bin/env python3
"""
Continue Fine-Tuning DistilBERT NER (Transformers 4.57.1)
==========================================================
Resumes from last checkpoint (61035)
Extends training for a few more epochs
Compatible with original training setup

Note: PII NER MODEL needs training on high cpu/memory GPU (e.g., Colab Pro+)

This model trained on Goole Colab Pro+ with the following specs:
- GPU: NVIDIA Tesla T4 (16GB)
- RAM: 52GB
- Disk: 300GB SSD
"""

import os, torch, numpy as np
from datasets import load_dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from collections import Counter
from seqeval.metrics import precision_score, recall_score, f1_score

# ------------------------------------------------------------
# ⚙️ CONFIG
# ------------------------------------------------------------
DATA_DIR = "/content/drive/MyDrive/Colab Notebooks/NER_data_clean"
CHECKPOINT_DIR = "/content/drive/MyDrive/Colab Notebooks/NER_models/pii_ner_v2/checkpoint-61035"
OUTPUT_DIR = "/content/drive/MyDrive/Colab Notebooks/NER_models/pii_ner_v3"
EPOCHS = 2
BATCH_SIZE = 16
LEARNING_RATE = 3e-5
WEIGHT_DECAY = 0.01
SEED = 42
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

torch.manual_seed(SEED)
np.random.seed(SEED)

# ------------------------------------------------------------
# 📦 DATA
# ------------------------------------------------------------
def _load_dataset():
    tpath = os.path.join(DATA_DIR, "train.jsonl")
    vpath = os.path.join(DATA_DIR, "validation.jsonl")
    ds = load_dataset("json", data_files={"train": tpath, "validation": vpath})
    return DatasetDict(train=ds["train"], test=ds["validation"])

ds = _load_dataset()

# ------------------------------------------------------------
# 🧩 TOKENIZER + MODEL
# ------------------------------------------------------------
print(f"📦 Loading model from {CHECKPOINT_DIR}")
tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT_DIR)
model = AutoModelForTokenClassification.from_pretrained(
    CHECKPOINT_DIR,
    use_safetensors=True,
    torch_dtype=torch.float32,
).to(DEVICE)

# ------------------------------------------------------------
# LABEL MAP
# ------------------------------------------------------------
labels_set = set()
for ex in ds["train"].select(range(min(2000, len(ds["train"])))):
    for s in ex.get("spans", []):
        labels_set.add(s["label"])

label_list = ["O"] + sorted({f"B-{l}" for l in labels_set} | {f"I-{l}" for l in labels_set})
id2label = {i: l for i, l in enumerate(label_list)}
label2id = {l: i for i, l in enumerate(label_list)}

# ------------------------------------------------------------
# ENCODING
# ------------------------------------------------------------
def convert_span_to_bio(text, spans, tokenizer, label_set):
    text = str(text)
    tokenized = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=256,
        return_offsets_mapping=True,
    )
    offsets = tokenized["offset_mapping"]
    labels = ["O"] * len(offsets)
    for span in spans or []:
        start, end, lbl = span.get("start"), span.get("end"), span.get("label")
        if lbl not in label_set:
            continue
        for j, (tok_start, tok_end) in enumerate(offsets):
            if tok_start >= start and tok_end <= end and tok_start < tok_end:
                labels[j] = f"B-{lbl}" if labels[j] == "O" else f"I-{lbl}"
    tokenized.pop("offset_mapping")
    tokenized["labels"] = [label2id.get(l, 0) for l in labels]
    return tokenized

def encode_batch(batch):
    all_input_ids, all_attention_masks, all_labels = [], [], []
    for text, spans in zip(batch["text"], batch["spans"]):
        enc = convert_span_to_bio(text, spans, tokenizer, labels_set)
        all_input_ids.append(enc["input_ids"])
        all_attention_masks.append(enc["attention_mask"])
        all_labels.append(enc["labels"])
    return {"input_ids": all_input_ids, "attention_mask": all_attention_masks, "labels": all_labels}

train_tok = ds["train"].map(encode_batch, batched=True)
eval_tok = ds["test"].map(encode_batch, batched=True)

# ------------------------------------------------------------
# METRICS
# ------------------------------------------------------------
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    true_preds, true_labels = [], []
    for p_row, l_row in zip(preds, labels):
        cur_p, cur_l = [], []
        for p, l in zip(p_row, l_row):
            if l != -100:
                cur_p.append(id2label[p])
                cur_l.append(id2label[l])
        true_preds.append(cur_p)
        true_labels.append(cur_l)
    return {
        "precision": precision_score(true_labels, true_preds),
        "recall": recall_score(true_labels, true_preds),
        "f1": f1_score(true_labels, true_preds),
    }

# ------------------------------------------------------------
# 🧠 TRAINING ARGS
# ------------------------------------------------------------
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    learning_rate=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
    eval_strategy="epoch",   # ✅ correct key name
    save_strategy="epoch",
    load_best_model_at_end=True,
    logging_steps=100,
    save_total_limit=2,
    metric_for_best_model="f1",
    report_to="none",
    fp16=False,
    seed=SEED,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_tok,
    eval_dataset=eval_tok,
    tokenizer=tokenizer,
    data_collator=DataCollatorForTokenClassification(tokenizer),
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)

# ------------------------------------------------------------
# 🚀 TRAIN
# ------------------------------------------------------------
print("🚀 Continuing fine-tuning...")
trainer.train(resume_from_checkpoint=CHECKPOINT_DIR)
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"✅ Model saved to {OUTPUT_DIR}")
print(trainer.evaluate())