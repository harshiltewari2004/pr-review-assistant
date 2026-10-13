"""Day 36: POST a real PR's cached diff to a running local service; print the top 3.

Usage:
    python -m scripts.day36_analyze_smoke --pr 8994 --diff-file <path>
    python -m scripts.day36_analyze_smoke --pr 8994 --diff-file <path> --as-new

--as-new sends a pr_number that isn't in the corpus, so the service treats the
diff as a brand-new PR: created now, nothing excluded.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.request
from pathlib import Path

from ingest.db import connect

URL = "http://localhost:7860/analyze"
REPO = "processing/p5.js"
AS_NEW_NUMBER = 999_999


async def pr_text(number: int):
    async with connect("local") as conn:
        return await conn.fetchrow(
            "SELECT title, body FROM pull_requests WHERE repo_id = 2 AND number = $1", number
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--diff-file", type=Path, required=True)
    parser.add_argument("--as-new", action="store_true")
    args = parser.parse_args()

    meta = asyncio.run(pr_text(args.pr))
    payload = {
        "repo": REPO,
        "pr_number": AS_NEW_NUMBER if args.as_new else args.pr,
        "title": meta["title"],
        "body": meta["body"],
        "diff": args.diff_file.read_text(),
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": os.environ["API_KEY"]},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.load(resp)
    for r in body["results"]:
        print(f"#{r['pr_number']:<5} {r['final_score']:.3f}  {r['reason']}")


if __name__ == "__main__":
    main()
