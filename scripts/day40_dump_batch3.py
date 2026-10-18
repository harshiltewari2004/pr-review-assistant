"""Day 40: blind text dump of batch-3 pairs (D-V11-5), for offline reading.

Every pair new to v1.1 (no batch 1-2 judgment), or only a --pairs subset.
Uses label.py's own render(): no score, rank, variant or author; the query's
outcome hidden. Candidates sorted by PR number, so no rank order leaks.
"New" means not judged in batches 1-2, so the dump is stable while batch 3
fills in, and the author's 30 stay in the full dump, unmarked, for the grader.

Usage:
    python -m scripts.day40_dump_batch3 --pairs eval/artifacts/kappa_subset_v11.json
    python -m scripts.day40_dump_batch3            # all 396, for the grader
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from eval.label import POOL_V11_PATH, PR_SQL, QUERIES_V11_SQL, RUBRIC, render, v11_query_ids
from ingest.db import connect

V10_JUDGED_SQL = "SELECT query_pr_id, candidate_pr_id FROM judgments WHERE batch IN (1, 2)"
NEW_PAIRS = 396  # D-V11-4


async def main() -> None:
    parser = argparse.ArgumentParser(description="Blind batch-3 dump (D-V11-5)")
    parser.add_argument("--pairs", type=Path, help="dump only these pairs")
    args = parser.parse_args()

    pool = {
        e["query_pr_id"]: e["candidate_pr_ids"]
        for e in json.loads(POOL_V11_PATH.read_text())["queries"]
    }
    async with connect("local") as conn:
        batch_ids = v11_query_ids(await conn.fetch(QUERIES_V11_SQL))
        old = {(r["query_pr_id"], r["candidate_pr_id"]) for r in await conn.fetch(V10_JUDGED_SQL)}
        pairs = {q: [c for c in pool[q] if (q, c) not in old] for q in batch_ids}
        assert sum(map(len, pairs.values())) == NEW_PAIRS, "pool/judgments drifted"
        if args.pairs:
            subset = {tuple(p) for p in json.loads(args.pairs.read_text())}
            assert subset <= {(q, c) for q in batch_ids for c in pairs[q]}, "subset outside batch 3"
            pairs = {q: [c for c in pairs[q] if (q, c) in subset] for q in batch_ids}
        ids = set(batch_ids) | {c for cs in pairs.values() for c in cs}
        prs = {r["id"]: r for r in await conn.fetch(PR_SQL, list(ids))}

    print(RUBRIC)
    n = 0
    shown = [q for q in batch_ids if pairs[q]]
    for qi, q in enumerate(shown, 1):
        print("\n" + "=" * 78)
        print(f"QUERY {qi}/{len(shown)}\n" + render(prs[q], "QUERY", show_outcome=False))
        for c in sorted(pairs[q], key=lambda c: prs[c]["number"]):
            n += 1
            print("\n" + "-" * 78)
            print(f"pair {n}  query #{prs[q]['number']} <- candidate #{prs[c]['number']}")
            print(render(prs[c], "CANDIDATE", show_outcome=True))
            print("GRADE:      REASON:")
    print(f"\n{n} pairs")


if __name__ == "__main__":
    asyncio.run(main())
