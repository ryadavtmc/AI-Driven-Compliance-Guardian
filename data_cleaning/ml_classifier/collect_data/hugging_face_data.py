from datasets import load_dataset
from collect_data_utils import load_and_save_dataset, hf_token

""" 
ai4privacy/pii-masking-300k (Hugging Face)
Source: Hugging Face Dataset
What’s inside: 300k+ samples of text with PII → names, emails, SSNs, etc.
Use for: Unsafe class, to diversify beyond finance docs.
Pros: Big size, covers lots of PII forms.
Cons: Not finance-only; mix of general text.
"""
# Choose your folder for dataset storage
RAW_DIR_1 = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/ml_classifier/huggingface/ai4privacy"

load_and_save_dataset("ai4privacy/pii-masking-300k", RAW_DIR_1)


""" 
BigCode PII in Code (for secrets like API keys / credentials)

Source: Hugging Face

What’s inside: API keys, secrets, emails, IPs inside code/config.

Use for: Unsafe class (secrets detection).

Pros: Critical for finance companies — API keys, tokens, configs are just as dangerous as PII.

Cons: Mostly code, so different style vs financial docs.
"""
# ds = load_dataset("bigcode/bigcode-pii-dataset", use_auth_token=True)
RAW_DIR_2 = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/ml_classifier/huggingface/bigcode"
# ds = load_dataset("bigcode/bigcode-pii-dataset", use_auth_token=True, cache_dir=RAW_DIR_2)
# load_and_save_dataset("bigcode/bigcode-pii-dataset", RAW_DIR_2)

if not hf_token:
    raise ValueError("No Hugging Face token found in .env file")

# Custom cache directory (optional)
RAW_DIR_2 = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/ml_classifier/huggingface/bigcode"

# Load gated dataset
ds = load_dataset("bigcode/bigcode-pii-dataset", token=hf_token, cache_dir=RAW_DIR_2)
print(ds)