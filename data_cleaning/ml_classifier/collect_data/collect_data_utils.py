import os
from dotenv import load_dotenv
from datasets import load_dataset

# Load environment variables from .env file
load_dotenv()

# Get token from env
hf_token = os.getenv("HF_TOKEN")

def load_and_save_dataset(hugging_face_path, local_path):
    try:
        ds = load_dataset(hugging_face_path, cache_dir=local_path)
        print(f"Dataset downloaded to: {local_path}")
    except Exception as e:
        print(f"Error: {e}")