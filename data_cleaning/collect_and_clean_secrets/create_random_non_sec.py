#!/usr/bin/env python3
"""
Synthetic Non-Secrets Generator
-------------------------------
Creates diverse fake "non-secrets" to reduce false positives in secret classification.

Output format:
{"text": "some fake line", "label": 0}
"""

import os
import random
import json
from pathlib import Path
import string

# -------------------
# Config
# -------------------
OUTPUT_FILE = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/processed/secrets_classifier/synthetic_non_secrets.jsonl"
NUM_SAMPLES = 50000  # how many synthetic lines to generate

# -------------------
# Generators
# -------------------
def random_gibberish(length=12):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def random_code_snippet():
    snippets = [
        "def process_data(df): return df.dropna()",
        "import numpy as np",
        "for i in range(10): print(i)",
        "class User(BaseModel): pass",
        "if value is None: return False"
    ]
    return random.choice(snippets)

def random_config_line():
    configs = [
        "USERNAME=guest",
        "API_KEY=notasecret123",
        "DEBUG=True",
        "TIMEOUT=30",
        "ENDPOINT_URL=http://localhost:8000"
    ]
    return random.choice(configs)

def random_log_line():
    logs = [
        "[INFO] Training completed successfully.",
        "[DEBUG] Connection established to database.",
        "[WARNING] Low memory detected.",
        "/usr/local/bin/start.sh",
        "C:\\Program Files\\MyApp\\app.exe"
    ]
    return random.choice(logs)

def random_sentence():
    sentences = [
        "The quick brown fox jumps over the lazy dog.",
        "Artificial intelligence is transforming industries.",
        "Unit tests should be deterministic and repeatable.",
        "Documentation is essential for maintainability.",
        "Always validate user input before processing."
    ]
    return random.choice(sentences)

# -------------------
# Weighted selection
# -------------------
def generate_non_secret():
    choice = random.choices(
        population=["gibberish", "code", "config", "log", "sentence"],
        weights=[0.4, 0.3, 0.15, 0.1, 0.05],  # adjust weights if needed
        k=1
    )[0]

    if choice == "gibberish":
        return random_gibberish(random.randint(8, 20))
    elif choice == "code":
        return random_code_snippet()
    elif choice == "config":
        return random_config_line()
    elif choice == "log":
        return random_log_line()
    else:
        return random_sentence()

# -------------------
# Main
# -------------------
def generate_dataset(n_samples, output_file):
    with open(output_file, "w") as f:
        for _ in range(n_samples):
            text = generate_non_secret()
            entry = {"text": text, "label": 0}
            f.write(json.dumps(entry) + "\n")
    print(f"✅ Generated {n_samples} synthetic non-secrets → {output_file}")

if __name__ == "__main__":
    generate_dataset(NUM_SAMPLES, OUTPUT_FILE)