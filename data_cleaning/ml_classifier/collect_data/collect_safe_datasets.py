from datasets import load_dataset
from collect_data_utils import load_and_save_dataset

# ag news dataset
# Choose your folder for dataset storage
RAW_DIR_AG_NEWS = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/ml_classifier/huggingface/ag_news"

load_and_save_dataset("ag_news", RAW_DIR_AG_NEWS)

# # weekipedia dataset
RAW_DIR_AG_WEEKI = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/ml_classifier/huggingface/ag_news"

load_dataset("wikimedia/wikipedia", "20231101.en", split="train[:100000]", cache_dir=RAW_DIR_AG_WEEKI)

# imdb dataset
RAW_DIR_AG_IMDB = "/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/data/raw/ml_classifier/huggingface/imdb"
load_and_save_dataset("imdb", RAW_DIR_AG_IMDB)