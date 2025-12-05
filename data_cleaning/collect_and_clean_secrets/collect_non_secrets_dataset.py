#!/usr/bin/env python3
"""
Non-Secrets Collection Script (for Negative Dataset)

Pipeline:
 1. Reads repo list from scanned_repos.txt.
 2. Skips repos already listed in scanned_non_secrets.txt.
 3. For each new repo:
    • Downloads repo ZIP (default branch, master.zip, or fallback git clone).
    • Extracts files, scans candidate lines.
    • Filters out lines that look like real secrets (entropy + regex).
    • Keeps up to MAX_PER_REPO random non-secrets.
    • Writes non-secrets into non_secrets.jsonl.
 4. Logs scanned repos into non_secret_scanned.txt (always, even if 0 collected).
 5. Logs failed repos into failed_repos.txt.
 6. Logs successful repos into scanned_non_secrets.txt.
 7. Deletes repo after processing (memory-efficient).
 8. Uses multithreading to process repos concurrently.
"""

import os
import re
import json
import math
import random
import requests
import threading
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------
# Config
# -------------------
load_dotenv()

BASE_DIR = Path("/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/notebooks/collect_and_create_secrets/")
CLONE_DIR = BASE_DIR / "clones"

INPUT_FILE = BASE_DIR / "scanned_repos.txt"
OUTPUT_FILE = BASE_DIR / "non_secrets_v3.jsonl"
LOG_FILE = BASE_DIR / "non_secret_scanned.txt"
FAILED_FILE = BASE_DIR / "failed_repos.txt"
SCANNED_FILE = BASE_DIR / "scanned_non_secrets.txt"   # NEW

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
THREADS = min(8, os.cpu_count() or 4)   # auto-set threads
MAX_PER_REPO = 100  # cap non-secret samples per repo

CLONE_DIR.mkdir(parents=True, exist_ok=True)

# -------------------
# Helpers
# -------------------
def entropy(s: str) -> float:
    """Shannon entropy to detect randomness (secrets)."""
    if not s:
        return 0
    prob = [float(s.count(c)) / len(s) for c in set(s)]
    return -sum(p * math.log(p, 2) for p in prob)

SECRET_PATTERNS = re.compile(
    r"(-----BEGIN|PRIVATE KEY|AWS_SECRET|xox[baprs]-|ghp_[0-9A-Za-z]{36}|AIzaSy|sk_live|secret|token|auth|passwd|bearer|PASSWORD)",
    re.I,
)

ALLOWED_SUFFIXES = {
    ".py", ".js", ".ts", ".go", ".java", ".rb", ".php", ".sh", ".yml", ".yaml",
    ".env", ".json", ".ini", ".xml", ".toml", ".cfg", ".conf", ".md", ".txt",
    ".c", ".cpp", ".h", ".cs", ".swift", ".scala", ".rs", ".dart", ".r", ".jl",
    ".sql"
}

def is_non_secret(line: str) -> bool:
    """Keep line unless it looks strongly like a secret."""
    line = line.strip()
    if not line or len(line) < 2 or len(line) > 800:
        return False
    if SECRET_PATTERNS.search(line):
        return False
    if entropy(line) > 5.5 and len(line) > 20:
        return False
    return True

def get_default_branch(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            return resp.json().get("default_branch", "main")
    except Exception as e:
        print(f"⚠️ Branch lookup failed for {owner}/{repo}: {e}")
    return "main"

def download_and_extract_repo(repo_fullname):
    """Try default branch ZIP, then master.zip, then git clone fallback."""
    try:
        owner, repo = repo_fullname.split("/")
        branch = get_default_branch(owner, repo)
        repo_path = CLONE_DIR / f"{repo}-{branch}"
        zip_file = CLONE_DIR / f"{repo}.zip"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

        # Try default branch
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        r = requests.get(zip_url, headers=headers, timeout=60)
        if r.status_code == 200:
            with open(zip_file, "wb") as f:
                f.write(r.content)
            os.system(f"unzip -q {zip_file} -d {CLONE_DIR}")
            return repo_path

        # Try master.zip
        alt_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
        r = requests.get(alt_url, headers=headers, timeout=60)
        if r.status_code == 200:
            with open(zip_file, "wb") as f:
                f.write(r.content)
            os.system(f"unzip -q {zip_file} -d {CLONE_DIR}")
            return CLONE_DIR / f"{repo}-master"

        # Fallback: git clone
        print(f"⚠️ ZIP failed for {repo_fullname}. Trying git clone...")
        os.system(f"git clone --depth 1 https://github.com/{owner}/{repo}.git {repo_path}")
        if repo_path.exists():
            return repo_path

    except Exception as e:
        print(f"⚠️ Failed to fetch {repo_fullname}: {e}")
    return None

def process_repo(repo_fullname):
    repo_path = download_and_extract_repo(repo_fullname)
    if not repo_path or not repo_path.exists():
        return [], False

    non_secrets = []
    try:
        for file in repo_path.rglob("*"):
            if not file.is_file():
                continue
            if file.suffix not in ALLOWED_SUFFIXES and file.name.lower() not in {"dockerfile", "makefile"}:
                continue
            try:
                with open(file, "r", errors="ignore") as f:
                    for line in f:
                        if is_non_secret(line):
                            non_secrets.append({
                                "text": line.strip(),
                                "repo": repo_fullname,
                                "file": str(file.relative_to(repo_path)),
                                "label": 0
                            })
            except Exception:
                continue
    finally:
        os.system(f"rm -rf {repo_path}")
        zip_file = CLONE_DIR / f"{repo_fullname.split('/')[1]}.zip"
        if zip_file.exists():
            zip_file.unlink()

    # Shuffle + sample
    if len(non_secrets) > MAX_PER_REPO:
        random.shuffle(non_secrets)
        non_secrets = non_secrets[:MAX_PER_REPO]

    return non_secrets, True

# -------------------
# Main
# -------------------
def collect_non_secrets():
    with open(INPUT_FILE) as f:
        repos = [line.strip() for line in f if line.strip()]

    # Load already scanned repos
    scanned_repos = set()
    if Path(SCANNED_FILE).exists():
        scanned_repos = set(Path(SCANNED_FILE).read_text().splitlines())

    repos = [r for r in repos if r not in scanned_repos]
    print(f"ℹ️ {len(repos)} repos to scan (skipping {len(scanned_repos)} already scanned)")

    lock = threading.Lock()
    total_non_secrets = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=THREADS) as executor, \
         open(OUTPUT_FILE, "a") as out, \
         open(LOG_FILE, "a") as log, \
         open(FAILED_FILE, "a") as fail_log, \
         open(SCANNED_FILE, "a") as scanned_log:

        futures = {executor.submit(process_repo, repo): repo for repo in repos}
        for future in tqdm(as_completed(futures), total=len(futures), desc="🔍 Collecting non-secrets"):
            repo = futures[future]
            try:
                lines, success = future.result()
                with lock:
                    log.write(repo + "\n")  # always log repo
                if success and lines:
                    with lock:
                        for entry in lines:
                            out.write(json.dumps(entry) + "\n")
                        total_non_secrets += len(lines)
                        scanned_log.write(repo + "\n")
                    print(f"📊 Repo {repo}: {len(lines)} non-secrets collected")
                elif not success:
                    with lock:
                        fail_log.write(repo + "\n")
                        failed_count += 1
                    print(f"❌ Repo {repo} failed")
                else:
                    with lock:
                        scanned_log.write(repo + "\n")  # mark scanned even if 0
                    print(f"ℹ️ Repo {repo}: 0 non-secrets")
            except Exception as e:
                with lock:
                    fail_log.write(repo + "\n")
                    failed_count += 1
                print(f"⚠️ Error {repo}: {e}")

    print(f"✅ Collected {total_non_secrets} non-secret lines total.")
    print(f"📦 Saved dataset → {OUTPUT_FILE}")
    print(f"📝 Logged repos → {LOG_FILE}")
    print(f"📝 Scanned repos tracked → {SCANNED_FILE}")
    print(f"❌ Failed repos: {failed_count} (saved to {FAILED_FILE})")

if __name__ == "__main__":
    collect_non_secrets()