"""Day 34: dump the round-2 re-grade set (D-P5-15).

Two sets, merged and unmarked in one blind dump:
- re-grade: every round-1 judgment at grade 1 or 2, except the author's 30
  (those are official); stored as round 2 after grading.
- measure: the author's 30 subset pairs; graded only to recompute kappa,
  never written to judgments.
Display is label.py's blind render: no grade, reason, score, rank, variant or
author; the query's own outcome hidden. Also writes
eval/artifacts/regrade_round2_pairs.json: [query_pr_id, candidate_pr_id,
batch, "regrade" | "measure"] rows, so the import can check coverage.

Usage: python -m scripts.day34_dump_regrade > ~/Desktop/regrade.txt
"""

from __future__ import annotations

import asyncio
import json
import sys

from eval.label import ARTIFACTS, PR_SQL, render
from ingest.db import connect

SUBSET_PATH = ARTIFACTS / "kappa_subset_batch2.json"
OUT_PATH = ARTIFACTS / "regrade_round2_pairs.json"
SUBSET_BATCH = 2

ROUND1_SQL = """
SELECT query_pr_id, candidate_pr_id, grade, batch FROM judgments WHERE round = 1
"""
ROUND2_COUNT_SQL = "SELECT count(*) FROM judgments WHERE round = 2"


async def main() -> None:
    subset = {tuple(p) for p in json.loads(SUBSET_PATH.read_text())}
    assert len(subset) == 30, len(subset)

    async with connect("local") as conn:
        assert await conn.fetchval(ROUND2_COUNT_SQL) == 0, "round 2 already has rows"
        round1 = await conn.fetch(ROUND1_SQL)
        judged = {(r["query_pr_id"], r["candidate_pr_id"]) for r in round1}
        assert subset <= judged, "subset pairs missing from round 1"

        rows = [
            (r["query_pr_id"], r["candidate_pr_id"], r["batch"], "regrade")
            for r in round1
            if r["grade"] > 0 and (r["query_pr_id"], r["candidate_pr_id"]) not in subset
        ]
        rows += [(q, c, SUBSET_BATCH, "measure") for q, c in subset]
        rows.sort(key=lambda r: (r[2], r[0], r[1]))

        ids = {r[0] for r in rows} | {r[1] for r in rows}
        prs = {r["id"]: r for r in await conn.fetch(PR_SQL, list(ids))}
    assert len(prs) == len(ids), "a pair references a missing PR"

    OUT_PATH.write_text(json.dumps([list(r) for r in rows], indent=2) + "\n")

    current_q = None
    for n, (q, c, _, _) in enumerate(rows, 1):
        if q != current_q:
            print("=" * 78)
            print(render(prs[q], "QUERY", show_outcome=False))
            current_q = q
        print("-" * 78)
        print(f"pair {n}: query #{prs[q]['number']} <- candidate #{prs[c]['number']}")
        print(render(prs[c], "CANDIDATE", show_outcome=True))
    print(f"\n{len(rows)} pairs")

    regrade = sum(1 for r in rows if r[3] == "regrade")
    print(
        f"wrote {OUT_PATH.name}: {regrade} regrade + {len(rows) - regrade} measure", file=sys.stderr
    )


if __name__ == "__main__":
    asyncio.run(main())
