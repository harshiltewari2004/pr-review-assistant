"""Freeze / thaw the PR list cache. D-P2-15.

The cache drifted three times (4,370 -> 4,371 -> 4,372) because the short
final page is re-fetched on every run. The second drift moved a measured
number and disguised a wrong prediction as an exact hit. Every published
exclusion count is computed against this snapshot, so it must not move.
"""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from ingest.github_client import PR_LIST_CACHE

PAGE_RE = re.compile(r"_page_(\d+)\.json$")


def _pages(slug: str) -> list[Path]:
    files = list(PR_LIST_CACHE.glob(f"{slug}_page_*.json"))
    return sorted(files, key=lambda p: int(PAGE_RE.search(p.name).group(1)))


def freeze(slug: str, reason: str) -> None:
    path = PR_LIST_CACHE / f"{slug}_MANIFEST.json"
    if path.exists():
        raise SystemExit(f"already frozen: {path}\n{path.read_text()}")

    files = _pages(slug)
    if not files:
        raise SystemExit(f"no cached pages for {slug}")

    numbers = [i["number"] for f in files for i in json.loads(f.read_text())]
    if len(set(numbers)) != len(numbers):
        raise SystemExit("duplicate PR numbers in cache — refusing to freeze")
    if numbers != sorted(numbers):
        raise SystemExit("cache not in ascending order — refusing to freeze")

    manifest = {
        "repo": slug.replace("__", "/"),
        "frozen_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pages": len(files),
        "total_prs": len(numbers),
        "first_pr_number": numbers[0],
        "last_pr_number": numbers[-1],
        "reason": reason,
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    print(f"\nFROZEN -> {path}")


def thaw(slug: str) -> None:
    path = PR_LIST_CACHE / f"{slug}_MANIFEST.json"
    if not path.exists():
        raise SystemExit(f"not frozen: {path}")
    print("THAWING. The snapshot below is the one every measured number so far")
    print("was computed against. Re-freeze immediately after re-fetching.\n")
    print(path.read_text())
    path.unlink()
    print(f"removed {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="processing__p5.js")
    ap.add_argument("--thaw", action="store_true")
    ap.add_argument(
        "--reason",
        default="D-P2-15 — every published exclusion count is measured against this snapshot",
    )
    args = ap.parse_args()
    thaw(args.slug) if args.thaw else freeze(args.slug, args.reason)
