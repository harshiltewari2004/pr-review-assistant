"""
Day 2 spike — GitHub API access (THROWAWAY).

Purpose (08_setup.md §8, 09_timeline_and_milestones.md Phase 1):
  Resolve the "can I read the GitHub API safely" unknown BEFORE Phase 2 builds
  ingest/github_client.py against it. Prove: pagination, rate-limit header
  handling, backoff, raw-diff fetch all work with a read-only PAT.

Side deliverable (07_testing.md §4-§5):
  Harvest 7 real fixture diffs from fastapi/fastapi into tests/fixtures/diffs/,
  auto-classified — including the @@-in-content case a naive parser splits wrong.

The PATTERNS here migrate into ingest/github_client.py in Phase 2. This file
gets archived after. It is not production code and app/ never imports it.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

OWNER, REPO = "fastapi", "fastapi"
API = "https://api.github.com"
FIXTURE_DIR = Path("tests/fixtures/diffs")

TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("GITHUB_TOKEN not set — put your read-only PAT in .env (08_setup.md §1)")

# X-GitHub-Api-Version pins the response shape. Unpinned, GitHub can change the
# payload underneath you with no warning — the exact failure mode 06 §11 warns
# about for deps, applied to an API.
JSON_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
# Confirmed via payload capture: this media type returns a raw unified diff,
# which is what the chunker needs (03_retrieval_engine.md §2).
DIFF_HEADERS = {**JSON_HEADERS, "Accept": "application/vnd.github.diff"}

# GitHub's SECONDARY limiter punishes rapid bursts independently of the hourly
# quota (04_architecture.md §5). A fixed inter-request delay is the cheapest way
# to stay under it.
INTER_REQUEST_DELAY = 0.5


def get(client: httpx.Client, url: str, headers: dict, *, max_retries: int = 5) -> httpx.Response:
    """One GET with rate-limit + backoff. The pattern Phase 2 inherits.

    Header names verified against the live API, not assumed.
    """
    for attempt in range(max_retries):
        resp = client.get(url, headers=headers)

        # Primary quota: back off proactively BEFORE hitting zero, so we never
        # trip a hard 403 mid-run (04_architecture.md §5).
        remaining = int(resp.headers.get("X-RateLimit-Remaining", "1"))
        if remaining < 100:
            reset_at = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(0, reset_at - time.time()) + 5
            print(f"  quota low ({remaining} left) — sleeping {wait:.0f}s")
            time.sleep(wait)

        # 403/429 here is the secondary limiter or a transient blip, NOT auth —
        # a bad token returns 401. Honour Retry-After if present, else backoff.
        if resp.status_code in (403, 429):
            retry_after = resp.headers.get("Retry-After")
            wait = int(retry_after) if retry_after else 2**attempt
            print(f"  {resp.status_code} — backing off {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
            continue

        resp.raise_for_status()
        time.sleep(INTER_REQUEST_DELAY)
        return resp

    raise RuntimeError(f"exhausted retries for {url}")


def list_prs(client: httpx.Client, pages: int, per_page: int = 100) -> list[dict]:
    """Paginate the PR list. state=all so merged, closed, and open all appear —
    the outcome mix matters for the corpus (01_evaluation_protocol.md §2)."""
    prs: list[dict] = []
    for page in range(1, pages + 1):
        url = (
            f"{API}/repos/{OWNER}/{REPO}/pulls"
            f"?state=all&per_page={per_page}&page={page}&sort=created&direction=desc"
        )
        resp = get(client, url, JSON_HEADERS)
        batch = resp.json()
        if not batch:
            break
        print(
            f"page {page}: {len(batch):>3} PRs  "
            f"quota {resp.headers['X-RateLimit-Remaining']}/{resp.headers['X-RateLimit-Limit']}"
        )
        prs.extend(batch)
    return prs


def fetch_diff(client: httpx.Client, number: int) -> str:
    return get(client, f"{API}/repos/{OWNER}/{REPO}/pulls/{number}", DIFF_HEADERS).text


def _largest_hunk_chars(diff: str) -> int:
    """Char size of the biggest @@hunk. A ROUGH proxy for token count -
    real truncation is measured with MiniLM'S tokenizer in
     Phase 3.This only nominates candidates.
    """
    hunks: list[list[str]] = []
    current: list[str] = []
    for line in diff.splitlines():
        if line.startswith("@@"):
            if current:
                hunks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        hunks.append(current)
    return max((sum(len(x) for x in h) for h in hunks), default=0)


def classify(diff: str) -> str | None:
    """Bucket a raw diff into one of the 7 fixtures categories .
    Order matters:Structural specials first,
    generic single/multi last -a binary diff is
    ALSO a single file-diff and we want the specific label.
    """
    file_blocks = diff.count("diff --git")

    if "Binary files" in diff or "GIT binary patch" in diff:
        return "binary_file"
    if "+++ /dev/null" in diff or "deleted file mode" in diff:
        return "deleted_file"
    if "rename from" in diff and "rename to " in diff and "@@" not in diff:
        return "rename_only"

    # @@-in-CONTENT: an @@ inside a body line, not a hunk header. Skip the
    # structural lines first (+++/---/index start with +/-/i), then flag any
    # content line ( , +, - prefix) that still contains @@. A naive splitter
    # breaks on exactly this (07_testing.md §5).

    for line in diff.splitlines():
        if line.startswith(
            ("+++", "---", "diff", "index", "@@", "new file", "deleted file", "rename")
        ):
            continue
        if line[:1] in (" ", "+", "-") and "@@" in line:
            return "at_marker_in_content"

    if _largest_hunk_chars(diff) > 1500:
        return "huge_hunk"

    if file_blocks == 1 and "@@" in diff:
        return "simple_single_file"
    if file_blocks > 1:
        return "multi_file"
    return None


# --- harvest -------------------------------------------------------------------

WANTED = {
    "simple_single_file",
    "multi_file",
    "binary_file",
    "deleted_file",
    "rename_only",
    "at_marker_in_content",
    "huge_hunk",
}


def harvest(client: httpx.Client, prs: list[dict]) -> dict[str, int]:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    found: dict[str, int] = {}
    for pr in prs:
        if WANTED <= found.keys():
            break  # got all 7
        num = pr["number"]
        try:
            diff = fetch_diff(client, num)
        except Exception as e:
            # Log and continue — one bad PR never kills the run (06 §8).
            print(f"  PR #{num}: diff fetch failed ({e}) — skip")
            continue
        cat = classify(diff)
        if cat and cat not in found:
            (FIXTURE_DIR / f"{cat}.diff").write_text(diff)
            found[cat] = num
            print(f"  ✓ {cat:22s} ← PR #{num}")

    missing = WANTED - found.keys()
    if missing:
        print(f"\n  STILL MISSING: {sorted(missing)}")
        print(
            "  → widen pages (arg 1), or hand-build from a real diff — the "
            "content is what the parser test cares about, not the provenance."
        )
    return found


def main() -> None:
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    with httpx.Client(timeout=30.0) as client:
        prs = list_prs(client, pages=pages)
        print(f"\nlisted {len(prs)} PRs across {pages} page(s)\n\nharvesting fixtures...")
        found = harvest(client, prs)
    print(f"\ndone — {len(found)}/7 fixtures in {FIXTURE_DIR}/")


if __name__ == "__main__":
    main()
