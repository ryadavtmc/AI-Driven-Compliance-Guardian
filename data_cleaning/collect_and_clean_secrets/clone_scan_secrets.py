#!/usr/bin/env python3
"""
Secrets Collection Script (Robust + Dynamic Repo Fetch)

Pipeline:
 1. Uses GitHub token for authentication.
 2. Fetches repos in star ranges (100k+, 50k+, 10k+, 5k+, etc.) until MAX_REPOS is reached.
 3. Writes repos to repos_v3.txt (deduplicated).
 4. Downloads repo ZIP tarball (or master.zip, or git clone fallback).
 5. Runs gitleaks with --no-git.
 6. Deduplication: avoids duplicates via Fingerprint.
 7. Checkpointing: resumes from last repo if interrupted.
 8. Repo skip list: avoids re-scanning repos already in scanned_repos.txt.
 9. Cleans extracted repos after scan to save disk.
"""

import os
import subprocess
import json
import requests
import time
import argparse
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

# -------------------
# Config
# -------------------
load_dotenv()

BASE_DIR = Path("/Users/debugger/Documents/github_repo/AI-Driven-Compliance-Guardian/notebooks/collect_and_create_secrets/")
CLONE_DIR = BASE_DIR / "clones"
REPOS_FILE = BASE_DIR / "repos_v5.2.txt"
OUTPUT_FILE = BASE_DIR / "leaks_v3.jsonl"
CHECKPOINT_FILE = BASE_DIR / "checkpoint.txt"
SCANNED_FILE = BASE_DIR / "scanned_repos.txt"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MAX_REPOS = 4000
STAR_BUCKETS = [100000, 50000, 10000, 5000, 1000]

PER_REPO_SLEEP = 0.9
CLONE_DIR.mkdir(parents=True, exist_ok=True)

# -------------------
# GitHub Helpers
# -------------------
def handle_rate_limit(resp):
    if resp.status_code == 403 and "X-RateLimit-Remaining" in resp.headers:
        reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
        sleep_time = max(reset_ts - int(time.time()), 60)
        print(f"⏸️ Rate limit hit. Sleeping {sleep_time}s...")
        time.sleep(sleep_time)
        return True
    return False

def get_default_branch(owner, repo, retries=2):
    """Fetch default branch from GitHub API (fallback to 'main')."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    url = f"https://api.github.com/repos/{owner}/{repo}"

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("default_branch", "main")
            elif handle_rate_limit(resp):
                continue
            else:
                print(f"⚠️ Error {resp.status_code} getting branch for {owner}/{repo}")
                break
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout fetching {owner}/{repo} (attempt {attempt}/{retries})")
        except Exception as e:
            print(f"⚠️ Error fetching {owner}/{repo} (attempt {attempt}/{retries}): {e}")
        time.sleep(2 ** attempt)  # exponential backoff

    # fallback if all retries fail
    print(f"⚠️ Falling back to 'main' for {owner}/{repo}")
    return "main"

def fetch_repos(language="Python"):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    repos = []
    for stars in STAR_BUCKETS:
        if len(repos) >= MAX_REPOS:
            break
        page = 1
        while len(repos) < MAX_REPOS:
            lang_filter = f"language:{language}+" if language.lower() != "all" else ""
            url = f"https://api.github.com/search/repositories?q={lang_filter}stars:>{stars}&sort=stars&order=desc&per_page=100&page={page}"
            resp = requests.get(url, headers=headers)
            if handle_rate_limit(resp):
                continue
            if resp.status_code != 200:
                print(f"⚠️ GitHub API error: {resp.status_code} {resp.text}")
                break
            items = resp.json().get("items", [])
            if not items:
                break
            for repo in items:
                full_name = repo["full_name"]
                if full_name not in repos:
                    repos.append(full_name)
            page += 1
    repos = repos[:MAX_REPOS]
    with open(REPOS_FILE, "w") as f:
        for r in repos:
            f.write(r + "\n")
    print(f"✅ Saved {len(repos)} repos to {REPOS_FILE}")

# -------------------
# Utils
# -------------------
def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ Error running {cmd}: {result.stderr.strip()}")
    return result.stdout.strip()

def load_existing_fingerprints():
    fps = set()
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for line in f:
                try:
                    leak = json.loads(line)
                    if "Fingerprint" in leak:
                        fps.add(leak["Fingerprint"])
                except:
                    continue
    return fps

def get_checkpoint():
    if CHECKPOINT_FILE.exists():
        return int(CHECKPOINT_FILE.read_text().strip())
    return 0

def save_checkpoint(idx):
    CHECKPOINT_FILE.write_text(str(idx))

def load_scanned_repos():
    if SCANNED_FILE.exists():
        return set(r.strip() for r in SCANNED_FILE.read_text().splitlines() if r.strip())
    return set()

def save_scanned_repo(repo_fullname):
    with open(SCANNED_FILE, "a") as f:
        f.write(repo_fullname + "\n")

def download_with_retries(url, dest, retries=2):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=60)
            if r.status_code == 200:
                with open(dest, "wb") as f:
                    f.write(r.content)
                return True
            elif handle_rate_limit(r):
                continue
            else:
                print(f"⚠️ Download failed ({r.status_code}), attempt {attempt+1}/{retries}")
        except Exception as e:
            print(f"⚠️ Error downloading {url}: {e}")
        time.sleep(2 ** attempt)
    return False

# -------------------
# Clone + Scan
# -------------------
def clone_and_scan(resume=False):
    with open(REPOS_FILE) as f:
        repos = [line.strip() for line in f if line.strip()]

    fingerprints = load_existing_fingerprints()
    scanned_repos = load_scanned_repos()
    start_idx = get_checkpoint() if resume else 0

    with open(OUTPUT_FILE, "a") as out_f:
        for i, repo_fullname in enumerate(
            tqdm(repos[start_idx:], desc="🔍 Scanning repos", initial=start_idx, total=len(repos))
        ):
            if repo_fullname in scanned_repos:
                print(f"⏭️ Skipping already scanned repo: {repo_fullname}")
                save_checkpoint(start_idx + i + 1)
                continue

            owner, repo = repo_fullname.split("/")
            branch = get_default_branch(owner, repo)
            repo_path = CLONE_DIR / f"{repo}-{branch}"
            zip_file = CLONE_DIR / f"{repo}.zip"
            zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

            if not download_with_retries(zip_url, zip_file):
                alt_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
                if not download_with_retries(alt_url, zip_file):
                    print(f"⚠️ ZIP failed for {repo_fullname}. Trying git clone...")
                    run_cmd(f"git clone --depth 1 https://github.com/{owner}/{repo}.git {repo_path}", cwd=CLONE_DIR)

            if not repo_path.exists() and not zip_file.exists():
                print(f"❌ Skipping {repo_fullname} (could not fetch)")
                save_checkpoint(start_idx + i + 1)
                continue

            if zip_file.exists():
                run_cmd(f"unzip -q {zip_file} -d {CLONE_DIR}")

            leak_file = repo_path / "gitleaks_report.json"
            run_cmd(f"gitleaks detect --no-git --report-format=json --report-path={leak_file}", cwd=repo_path)

            if leak_file.exists():
                try:
                    leaks = json.load(open(leak_file))
                    new_count = 0
                    for leak in leaks:
                        fp = leak.get("Fingerprint")
                        if fp and fp not in fingerprints:
                            out_f.write(json.dumps(leak) + "\n")
                            fingerprints.add(fp)
                            new_count += 1
                    print(f"📊 Repo: {repo_fullname} → {new_count} new leaks added")
                except Exception as e:
                    print(f"⚠️ Failed parsing {leak_file}: {e}")

            run_cmd(f"rm -rf {repo_path}")
            if zip_file.exists():
                zip_file.unlink()

            save_checkpoint(start_idx + i + 1)
            save_scanned_repo(repo_fullname)
            time.sleep(PER_REPO_SLEEP)

    print(f"✅ Finished. Results saved to {OUTPUT_FILE}")

# -------------------
# Main
# -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Repo Secret Scanner with Gitleaks")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--language", default="Python", help="Language filter (e.g., Python, JavaScript, Go, all)")
    args = parser.parse_args()

    if not GITHUB_TOKEN:
        print("❌ Missing GITHUB_TOKEN. Please set it with: export GITHUB_TOKEN=your_token")
        exit(1)

    if not REPOS_FILE.exists():
        fetch_repos(language=args.language)
    clone_and_scan(resume=args.resume)

"""
Usage:
  • python3 clone_scan_secrets.py --language Python   (just Python repos)
  • python3 clone_scan_secrets.py --language all      (all repos, regardless of language)
"""