"""Generate the demo page's seeded examples and metric strip (05 §5). D-P8-1..3.

Seed rule (D-P8-3, committed before any result was seen): the SEED_COUNT most
recent processing/p5.js PRs opened after the corpus snapshot, not authored by
a bot, whose diff keeps at least one hunk after the chunker's exclusions.
Each runs through app.service.analyze_diff (the live bot's pipeline) as a NEW
PR, against the local evaluated snapshot. Whatever comes out is shown.

Strip numbers are derived from holdout_v11_scored.json and pool_v11.json, never typed
(10 §8: every figure traces to the harness). Raw diffs cached to .cache/seeds/
(invariant 19).

Usage: python -m scripts.generate_seeds
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from app.retrieval.chunking import parse_hunks
from app.retrieval.constants import EMBEDDING_MODEL, VECTOR_AGGREGATION
from app.retrieval.embedding import get_model
from app.retrieval.scoring import DEFAULT_WEIGHTS
from app.retrieval.signals import build_bm25_index
from app.service import CORPUS_COUNT_SQL, REPO_SQL, analyze_diff
from ingest.db import connect

REPO = "processing/p5.js"
SEED_COUNT = 3
SCAN_LIMIT = 100  # newest PRs scanned to find SEED_COUNT that qualify
API = "https://api.github.com"
ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = ROOT / "eval/artifacts/corpus_snapshot.json"
HOLDOUT_PATH = ROOT / "eval/artifacts/holdout_v11_scored.json"  # D-V11-10
POOL_PATH = ROOT / "eval/artifacts/pool_v11.json"
# D-P8-3's cutoff, pinned: the rule names this date, and corpus_snapshot's
# indexed_at moved to 2026-10-17 when D-V11-3 re-ran the index (content unchanged).
SNAPSHOT_CUTOFF = datetime.fromisoformat("2026-08-15T07:29:33.633256+00:00")
CACHE_DIR = ROOT / ".cache/seeds"
OUT_PATH = ROOT / "frontend/seed_results.json"
OUT_JS_PATH = ROOT / "frontend/seed_results.js"
RULE = (
    "the 3 most recent processing/p5.js PRs opened after the corpus snapshot, "
    "not authored by a bot, whose diff keeps at least one hunk after chunker exclusions"
)


def github(path: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(
        API + path,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def pick_seeds(snapshot_at: datetime) -> list[tuple[dict, str]]:
    """Apply the D-P8-3 rule, newest first. Diffs cached before parsing."""
    prs = json.loads(
        github(f"/repos/{REPO}/pulls?state=all&sort=created&direction=desc&per_page={SCAN_LIMIT}")
    )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    picked = []
    for pr in prs:
        if datetime.fromisoformat(pr["created_at"]) <= snapshot_at:
            break
        if pr["user"]["type"] == "Bot":
            continue
        diff_path = CACHE_DIR / f"{pr['number']}.diff"
        if not diff_path.exists():
            diff_path.write_bytes(
                github(f"/repos/{REPO}/pulls/{pr['number']}", "application/vnd.github.diff")
            )
        diff = diff_path.read_text()
        if not parse_hunks(diff):
            continue
        picked.append((pr, diff))
        if len(picked) == SEED_COUNT:
            break
    assert len(picked) == SEED_COUNT, f"only {len(picked)} qualifying PRs"
    return picked


def strip_metrics() -> dict:
    """D-P8-1 numbers, derived from the harness artifacts. D-P8-4, D-V11-10."""
    holdout = json.loads(HOLDOUT_PATH.read_text())
    w = DEFAULT_WEIGHTS
    locked = {"vector": w.vector, "file_overlap": w.file_overlap, "bm25": w.bm25}
    assert holdout["weights"] == locked, "holdout scored at other weights than the page uses"
    vs = holdout["lenient_minus_bm25_only"]
    rr = [p["mrr_lenient"] for p in holdout["per_query"]]
    pool = json.loads(POOL_PATH.read_text())
    return {
        "top_result_relevant": sum(1 for v in rr if v == 1.0),
        "holdout_queries": len(rr),
        "judged_pairs": sum(len(q["candidate_pr_ids"]) for q in pool["queries"]),
        "relevant_at_rank_pct": [round(100 * r["lenient"]) for r in holdout["per_rank"]],
        "vs_keyword": {
            "recall_gain": vs["mean"],
            "ci95": vs["ci95"],
            "beats": vs["beats_bm25_only"],
        },
        "source": "eval/artifacts/holdout_v11_scored.json, eval/artifacts/pool_v11.json",
    }


async def main() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    seeds = pick_seeds(SNAPSHOT_CUTOFF)

    async with connect("local") as conn:
        repo_id = await conn.fetchval(REPO_SQL, REPO)
        index = await build_bm25_index(conn, repo_id)
        corpus_prs = await conn.fetchval(CORPUS_COUNT_SQL, repo_id)
        await asyncio.to_thread(get_model)
        queries = []
        for pr, diff in seeds:
            results = await analyze_diff(
                conn,
                index,
                repo=REPO,
                repo_id=repo_id,
                title=pr["title"],
                body=pr["body"],
                diff=diff,
                known_pr_number=None,
            )
            queries.append(
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "url": pr["html_url"],
                    "created_at": pr["created_at"],
                    "results": [r.model_dump() for r in results],
                }
            )

    w = DEFAULT_WEIGHTS
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rule": RULE,
        "seed_cutoff": SNAPSHOT_CUTOFF.isoformat(),
        "weights": {"vector": w.vector, "file_overlap": w.file_overlap, "bm25": w.bm25},
        "aggregation": VECTOR_AGGREGATION,
        "model": EMBEDDING_MODEL,
        "corpus": {
            "repo": REPO,
            "in_corpus_prs": corpus_prs,
            "indexed_at": snapshot["indexed_at"],
            "fingerprint": snapshot["corpus_fingerprint"],
        },
        "metrics": strip_metrics(),
        "queries": queries,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    # Loaded with a <script> tag, not fetch(): no network call on load (05 §5),
    # and the page works even when opened straight from disk.
    OUT_JS_PATH.write_text("window.SEEDS = " + json.dumps(payload, ensure_ascii=False) + ";\n")

    m = payload["metrics"]
    print(
        f"strip: top result relevant {m['top_result_relevant']}/{m['holdout_queries']}, "
        f"{m['judged_pairs']} judged pairs"
    )
    vk = m["vs_keyword"]
    print(f"strip: relevant at rank 1/2/3: {m['relevant_at_rank_pct']} %")
    print(f"strip: vs keyword-only {vk['recall_gain']:+.3f} CI {vk['ci95']} beats={vk['beats']}")
    for q in queries:
        print(f"\n#{q['number']}  {q['title']}")
        for r in q["results"]:
            print(f"   #{r['pr_number']:<5} {r['final_score']:.3f}  {r['title']}")


if __name__ == "__main__":
    asyncio.run(main())
