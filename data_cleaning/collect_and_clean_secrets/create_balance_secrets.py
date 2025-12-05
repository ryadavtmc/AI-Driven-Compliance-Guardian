import os
import json
import random
import pandas as pd
from sklearn.model_selection import train_test_split

# -------------------
# Config
# -------------------
DATA_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/secrets"
OUT_DIR = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/secrets_classifier"

os.makedirs(OUT_DIR, exist_ok=True)

SECRET_FILES = [
    "real_secrets.jsonl",
    "dummy_secrets.jsonl",
    "all_secrets_clean.jsonl",
]

NON_SECRET_FILES = [
    "non_secrets_stack_abap.jsonl",
    "non_secrets_stack_go.jsonl",
    "non_secrets_stack_java.jsonl",
    "non_secrets_stack_javascript.jsonl",
    "non_secrets_stack_python.jsonl",
]

# -------------------
# Helper Functions
# -------------------
def load_jsonl(path):
    data = []
    if not os.path.exists(path):
        print(f"⚠️ File not found: {path}")
        return data
    with open(path, "r") as f:
        for line in f:
            try:
                obj = json.loads(line)
                text = obj.get("text") or obj.get("Secret") or obj.get("Match")
                if text and len(text.strip()) > 5:
                    data.append({"text": text.strip(), "label": 1})
            except json.JSONDecodeError:
                continue
    print(f"📥 Loaded {len(data)} secrets from {os.path.basename(path)}")
    return data

def load_non_secrets(path):
    data = []
    if not os.path.exists(path):
        print(f"⚠️ File not found: {path}")
        return data
    with open(path, "r") as f:
        for line in f:
            try:
                obj = json.loads(line)
                text = obj.get("text")
                if text and len(text.strip()) > 5:
                    data.append({"text": text.strip(), "label": 0})
            except json.JSONDecodeError:
                continue
    print(f"📥 Loaded {len(data)} non-secrets from {os.path.basename(path)}")
    return data

# -------------------
# Load secrets
# -------------------
all_secrets = []
for f in SECRET_FILES:
    all_secrets.extend(load_jsonl(os.path.join(DATA_DIR, f)))
print(f"🔐 Total secrets loaded: {len(all_secrets)}")

# -------------------
# Load non-secrets
# -------------------
all_nonsecrets = []
for f in NON_SECRET_FILES:
    all_nonsecrets.extend(load_non_secrets(os.path.join(DATA_DIR, f)))
print(f"🧩 Total non-secrets loaded: {len(all_nonsecrets)}")

# -------------------
# Balance dataset
# -------------------
if len(all_secrets) == 0 or len(all_nonsecrets) == 0:
    raise ValueError("❌ No secrets or non-secrets loaded. Check file paths or data format.")

N = min(len(all_secrets), len(all_nonsecrets))
random.shuffle(all_secrets)
random.shuffle(all_nonsecrets)

balanced = all_secrets[:N] + all_nonsecrets[:N]
random.shuffle(balanced)

print(f"⚖️ Balancing to {N} samples per class")
print(f"📊 Final label counts: Secrets={N}, Non-secrets={N}")

# -------------------
# Split train/val/test
# -------------------
train, temp = train_test_split(balanced, test_size=0.2, random_state=42)
val, test = train_test_split(temp, test_size=0.5, random_state=42)

# -------------------
# Save v2 dataset
# -------------------
def save_jsonl(path, data):
    with open(path, "w") as f:
        for d in data:
            f.write(json.dumps(d) + "\n")

save_jsonl(os.path.join(OUT_DIR, "balanced_train_v2.jsonl"), train)
save_jsonl(os.path.join(OUT_DIR, "balanced_val_v2.jsonl"), val)
save_jsonl(os.path.join(OUT_DIR, "balanced_test_v2.jsonl"), test)

print("\n✅ Saved balanced dataset v2:")
print(f"  • Train: {len(train)}")
print(f"  • Val:   {len(val)}")
print(f"  • Test:  {len(test)}")