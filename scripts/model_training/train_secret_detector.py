#!/usr/bin/env python3
"""
BERT Secret Classifier Trainer + Evaluator (Clean v2)
-----------------------------------------------------
Trains DistilRoBERTa on Gitleaks-verified balanced datasets.

Input:
    balanced_clean_train_v2.jsonl
    balanced_clean_test_v2.jsonl
Output:
    models/bert_secret_clf_v2/
    ml_model_eval_results.csv (appended with new metrics)
"""

import os
import re
import math
import json
import torch
import torch.nn as nn
import pandas as pd
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModel,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback,
    __version__ as HF_VERSION,
)
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    average_precision_score,
    roc_auc_score,
    f1_score,
)
import matplotlib.pyplot as plt

# -------------------
# Paths
# -------------------
BASE_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/secrets_classifier/"
TRAIN_FILE = os.path.join(BASE_DIR, "balanced_clean_train_v2.jsonl")
TEST_FILE  = os.path.join(BASE_DIR, "balanced_clean_test_v2.jsonl")
OUTPUT_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/models/secret_detector"
RESULTS_FILE = os.path.join(BASE_DIR, "ml_model_eval_results.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------
# Hyperparameters
# -------------------
MODEL_NAME = "distilroberta-base"
BATCH_SIZE = 16
EPOCHS = 4
LR = 2e-5
MAX_LEN = 128

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------
# Feature helpers
# -------------------
def entropy(s: str) -> float:
    if not s:
        return 0.0
    probs = [float(s.count(c)) / len(s) for c in set(s)]
    return -sum(p * math.log(p, 2) for p in probs)

def extra_features(text):
    looks_jwt = 1 if re.search(r"eyJ[a-zA-Z0-9_-]{10,}\.", text) else 0
    looks_key = 1 if re.search(r"(sk_|ghp_|AKIA|AIza)", text) else 0
    return [len(text), entropy(text), looks_jwt, looks_key]

# -------------------
# Dataset
# -------------------
class SecretsDataset(Dataset):
    def __init__(self, path, tokenizer, max_len=128):
        self.data = []
        with open(path, "r") as f:
            for line in f:
                try:
                    self.data.append(json.loads(line))
                except:
                    continue
        self.texts = [str(d["text"]) for d in self.data]
        self.labels = [int(d["label"]) for d in self.data]
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        text = self.texts[idx]
        enc = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt",
        )
        feats = extra_features(text)
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "features": torch.tensor(feats, dtype=torch.float),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }

# -------------------
# Model (BERT + extra features)
# -------------------
class SecretClassifier(nn.Module):
    def __init__(self, model_name, num_labels=2, extra_dim=4):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.3)
        hidden_size = self.bert.config.hidden_size
        self.classifier = nn.Linear(hidden_size + extra_dim, num_labels)

    def forward(self, input_ids, attention_mask, features, labels=None):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        x = torch.cat([cls, features], dim=1)
        x = self.dropout(x)
        logits = self.classifier(x)
        loss = None
        if labels is not None:
            loss = nn.CrossEntropyLoss()(logits, labels)
        return {"loss": loss, "logits": logits}

# -------------------
# Build TrainingArguments
# -------------------
def build_training_args(output_dir):
    valid_args = TrainingArguments.__init__.__code__.co_varnames
    kwargs = dict(
        output_dir=output_dir,
        learning_rate=LR,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        num_train_epochs=EPOCHS,
        weight_decay=0.01,
        logging_dir=os.path.join(output_dir, "logs"),
        logging_steps=100,
    )
    has_eval = False
    if "evaluation_strategy" in valid_args:
        kwargs["evaluation_strategy"] = "epoch"
        has_eval = True
    elif "evaluate_during_training" in valid_args:
        kwargs["evaluate_during_training"] = True
        has_eval = True

    if "save_strategy" in valid_args:
        kwargs["save_strategy"] = "epoch"
    else:
        kwargs["save_steps"] = 500

    if "load_best_model_at_end" in valid_args and has_eval:
        kwargs["load_best_model_at_end"] = True
        kwargs["metric_for_best_model"] = "eval_loss"
        kwargs["greater_is_better"] = False
    else:
        kwargs["load_best_model_at_end"] = False

    return TrainingArguments(**kwargs), has_eval

# -------------------
# Train & Evaluate
# -------------------
print(f"🤗 Transformers version: {HF_VERSION}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
train_ds = SecretsDataset(TRAIN_FILE, tokenizer, MAX_LEN)
test_ds  = SecretsDataset(TEST_FILE,  tokenizer, MAX_LEN)
print(f"✓ Train size: {len(train_ds)} | Test size: {len(test_ds)}")

model = SecretClassifier(MODEL_NAME).to(device)
training_args, has_eval = build_training_args(OUTPUT_DIR)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = logits.argmax(axis=-1)
    f1 = f1_score(labels, preds, average="weighted", zero_division=0)
    report = classification_report(labels, preds, output_dict=True, zero_division=0)
    return {
        "precision": report["weighted avg"]["precision"],
        "recall":    report["weighted avg"]["recall"],
        "f1":        f1,
        "acc":       report["accuracy"],
    }

callbacks = []
if getattr(training_args, "load_best_model_at_end", False):
    callbacks.append(EarlyStoppingCallback(early_stopping_patience=2))

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=test_ds,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
    callbacks=callbacks,
)

trainer.train()

# -------------------
# Final Evaluation
# -------------------
pred = trainer.predict(test_ds)
y_true = pred.label_ids
y_scores = pred.predictions[:, 1]
y_pred = pred.predictions.argmax(axis=1)

print("\n📊 Classification Report:\n", classification_report(y_true, y_pred, digits=4))
print("Confusion Matrix:\n", confusion_matrix(y_true, y_pred))

prec, rec, _ = precision_recall_curve(y_true, y_scores)
ap = average_precision_score(y_true, y_scores)
roc_auc = roc_auc_score(y_true, y_scores)

plt.figure(figsize=(6,5))
plt.plot(rec, prec, label=f"DistilRoBERTa (AP={ap:.2f})")
plt.xlabel("Recall"); plt.ylabel("Precision")
plt.title("Precision-Recall Curve (Clean v2)")
plt.legend(); plt.grid(); plt.tight_layout(); plt.show()

# -------------------
# Save results
# -------------------
results = {
    "model": "DistilRoBERTa_v2",
    "auc": roc_auc,
    "precision": classification_report(y_true, y_pred, output_dict=True)["weighted avg"]["precision"],
    "recall": classification_report(y_true, y_pred, output_dict=True)["weighted avg"]["recall"],
    "f1": classification_report(y_true, y_pred, output_dict=True)["weighted avg"]["f1-score"],
    "best_threshold": None,
    "best_f1": None,
    "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
}

df_results = pd.DataFrame([results])
if os.path.exists(RESULTS_FILE):
    prev = pd.read_csv(RESULTS_FILE)
    df_results = pd.concat([prev, df_results], ignore_index=True)
df_results.to_csv(RESULTS_FILE, index=False)

print(f"📦 Saved evaluation results → {RESULTS_FILE}")

# -------------------
# Save model
# -------------------
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"💾 Saved model to {OUTPUT_DIR}")