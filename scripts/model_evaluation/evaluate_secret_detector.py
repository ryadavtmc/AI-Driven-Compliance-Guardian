#!/usr/bin/env python3
"""
DistilRoBERTa Secret Detector — Evaluation v3 (safetensors + architecture fix)
=============================================================================
Loads the fine-tuned model (with extra handcrafted features)
and evaluates it on balanced_clean_test_v2.jsonl.

✅ Supports both .bin and .safetensors
✅ Reconstructs the custom classifier architecture
✅ Saves metrics + charts under evaluation/secret_detector/
"""

import os, re, math, json, torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from torch.utils.data import Dataset
from transformers import AutoTokenizer, AutoModel
from safetensors.torch import load_file as safe_load
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_curve,
    average_precision_score, accuracy_score, f1_score
)

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
BASE_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/secrets_classifier/balanced_clean_test_v2.jsonl")
MODEL_DIR = os.path.join(BASE_DIR, "models/secret_detector")
EVAL_DIR  = os.path.join(BASE_DIR, "evaluation/secret_detector")
os.makedirs(EVAL_DIR, exist_ok=True)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ------------------------------------------------------------
# FEATURE HELPERS
# ------------------------------------------------------------
def entropy(s: str) -> float:
    if not s:
        return 0.0
    p = [s.count(c)/len(s) for c in set(s)]
    return -sum(pi * math.log(pi, 2) for pi in p)

def extra_features(text):
    """Extract handcrafted regex + numeric features."""
    looks_jwt = 1 if re.search(r"eyJ[a-zA-Z0-9_-]{10,}\.", text) else 0
    looks_key = 1 if re.search(r"(sk_|ghp_|AKIA|AIza)", text) else 0
    return [len(text), entropy(text), looks_jwt, looks_key]

# ------------------------------------------------------------
# DATASET
# ------------------------------------------------------------
class SecretsEvalDataset(Dataset):
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
        return len(self.texts)

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

# ------------------------------------------------------------
# MODEL (MATCHES TRAINING)
# ------------------------------------------------------------
class SecretClassifier(torch.nn.Module):
    def __init__(self, model_name, num_labels=2, extra_dim=4):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name, ignore_mismatched_sizes=True)
        self.dropout = torch.nn.Dropout(0.3)
        hidden_size = self.bert.config.hidden_size
        self.classifier = torch.nn.Linear(hidden_size + extra_dim, num_labels)

    def forward(self, input_ids, attention_mask, features, labels=None):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        x = torch.cat([cls, features], dim=1)
        x = self.dropout(x)
        logits = self.classifier(x)
        loss = None
        if labels is not None:
            loss = torch.nn.CrossEntropyLoss()(logits, labels)
        return {"loss": loss, "logits": logits}

# ------------------------------------------------------------
# LOAD MODEL + TOKENIZER
# ------------------------------------------------------------
print(f"📦 Loading model from: {MODEL_DIR}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

# Load safetensors or fallback
safe_path = os.path.join(MODEL_DIR, "model.safetensors")
bin_path = os.path.join(MODEL_DIR, "pytorch_model.bin")

if os.path.exists(safe_path):
    print(f"✅ Found safetensors model: {safe_path}")
    state_dict = safe_load(safe_path)
elif os.path.exists(bin_path):
    print(f"✅ Found pytorch_model.bin: {bin_path}")
    state_dict = torch.load(bin_path, map_location="cpu")
else:
    raise FileNotFoundError(f"❌ No model weights found in {MODEL_DIR}")

model = SecretClassifier("distilroberta-base")
missing, unexpected = model.load_state_dict(state_dict, strict=False)
if missing:
    print(f"⚠️ Missing keys: {missing}")
if unexpected:
    print(f"⚠️ Unexpected keys: {unexpected}")

model.to(DEVICE)
model.eval()
print("✅ Custom DistilRoBERTa model loaded successfully.")

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
dataset = SecretsEvalDataset(DATA_PATH, tokenizer)
print(f"📂 Loaded {len(dataset)} evaluation samples.")

# ------------------------------------------------------------
# INFERENCE
# ------------------------------------------------------------
y_true, y_pred, y_score = [], [], []
print("🚀 Running inference...")
for item in tqdm(dataset, desc="Evaluating", unit="sample"):
    input_ids = item["input_ids"].unsqueeze(0).to(DEVICE)
    mask = item["attention_mask"].unsqueeze(0).to(DEVICE)
    feats = item["features"].unsqueeze(0).to(DEVICE)
    label = item["labels"].item()

    with torch.no_grad():
        out = model(input_ids=input_ids, attention_mask=mask, features=feats)
        logits = out["logits"].squeeze(0).cpu().numpy()
        probs = torch.softmax(torch.tensor(logits), dim=-1).numpy()

    y_true.append(label)
    y_pred.append(np.argmax(probs))
    y_score.append(probs[1])

y_true, y_pred, y_score = np.array(y_true), np.array(y_pred), np.array(y_score)

# ------------------------------------------------------------
# METRICS
# ------------------------------------------------------------
report = classification_report(y_true, y_pred, target_names=["non-secret", "secret"], digits=4)
print("\n📊 Classification Report:\n", report)

cm = confusion_matrix(y_true, y_pred)
acc = accuracy_score(y_true, y_pred)
f1w = f1_score(y_true, y_pred, average="weighted")
roc_auc = roc_auc_score(y_true, y_score)
prec, rec, _ = precision_recall_curve(y_true, y_score)
pr_auc = average_precision_score(y_true, y_score)

summary = {
    "accuracy": acc,
    "f1_weighted": f1w,
    "roc_auc": roc_auc,
    "pr_auc": pr_auc,
    "support_secret": int(sum(y_true)),
    "support_non_secret": int(len(y_true) - sum(y_true)),
}
print("\n✅ Metrics Summary:", json.dumps(summary, indent=2))

# ------------------------------------------------------------
# VISUALS
# ------------------------------------------------------------
plt.figure(figsize=(5,5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=["non-secret","secret"],
            yticklabels=["non-secret","secret"])
plt.xlabel("Predicted"); plt.ylabel("True")
plt.title("Confusion Matrix — DistilRoBERTa Secret Detector")
plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "confusion_matrix.png"))
plt.close()

# ROC curve
from sklearn.metrics import roc_curve
fpr, tpr, _ = roc_curve(y_true, y_score)
plt.figure(figsize=(5,5))
plt.plot(fpr, tpr, label=f"ROC AUC = {roc_auc:.3f}")
plt.plot([0,1],[0,1],"--",color="gray")
plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
plt.title("ROC Curve — Secret Detector")
plt.legend(); plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "roc_curve.png"))
plt.close()

# Precision-Recall curve
plt.figure(figsize=(5,5))
plt.plot(rec, prec, label=f"PR AUC = {pr_auc:.3f}")
plt.xlabel("Recall"); plt.ylabel("Precision")
plt.title("Precision-Recall Curve — Secret Detector")
plt.legend(); plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "pr_curve.png"))
plt.close()

# ------------------------------------------------------------
# SAVE METRICS
# ------------------------------------------------------------
with open(os.path.join(EVAL_DIR, "metrics_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

pd.DataFrame(classification_report(y_true, y_pred, output_dict=True)).to_csv(
    os.path.join(EVAL_DIR, "classification_report.csv")
)

print(f"💾 All evaluation artifacts saved → {EVAL_DIR}")
print("\n🏁 Evaluation complete!")