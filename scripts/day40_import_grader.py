"""Day 40: import the v1.1 grader's batch-3 grades (D-V11-1 §4, D-V11-6).

Reads eval/artifacts/batch3_claude_grades.psv (query#|candidate#|grade|reason).
Checks it covers exactly the 396 pairs new to v1.1 (pool_v11 minus batch 1-2
judgments). The author's 30 are skipped: theirs are official (D-V11-5); the
grader's grades for them exist only to measure agreement. Only those 30 may
already be judged; the rest are inserted as round 1, batch 3, in one
transaction. Dry run unless --apply. Never overwrites (invariant 15).

Usage:
    python -m scripts.day40_import_grader
    python -m scripts.day40_import_grader --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter

from eval.label import ARTIFACTS, INSERT_SQL, LABELER_LOGIN, POOL_V11_PATH, ROUND, V11_BATCH
from ingest.db import connect
from scripts.day40_dump_batch3 import NEW_PAIRS, V10_JUDGED_SQL
from scripts.day40_import_author import PRS_SQL, REPO_ID, SUBSET_PATH, load_grades

GRADES_PATH = ARTIFACTS / "batch3_claude_grades.psv"
ROUND1_SQL = "SELECT query_pr_id, candidate_pr_id FROM judgments WHERE round = $1"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import the v1.1 grader's grades (D-V11-6)")
    parser.add_argument("--apply", action="store_true", help="write (default: dry run)")
    args = parser.parse_args()

    grades = load_grades(GRADES_PATH.read_text())
    subset = {tuple(p) for p in json.loads(SUBSET_PATH.read_text())}
    pool = {
        e["query_pr_id"]: e["candidate_pr_ids"]
        for e in json.loads(POOL_V11_PATH.read_text())["queries"]
    }
    numbers = sorted({n for q, c, *_ in grades for n in (q, c)})

    async with connect("local") as conn:
        prs = {r["number"]: r for r in await conn.fetch(PRS_SQL, REPO_ID, numbers)}
        assert len(prs) == len(numbers), "file names a PR number not in the corpus"
        old = {(r["query_pr_id"], r["candidate_pr_id"]) for r in await conn.fetch(V10_JUDGED_SQL)}
        expected = {(q, c) for q, cs in pool.items() for c in cs if (q, c) not in old}
        assert len(expected) == NEW_PAIRS, len(expected)

        keys = [(prs[q]["id"], prs[c]["id"]) for q, c, *_ in grades]
        assert len(set(keys)) == len(keys), "a pair appears twice"
        assert set(keys) == expected, "grades must cover exactly the new pairs"
        assert subset <= expected, "subset outside the new pairs"
        judged = {
            (r["query_pr_id"], r["candidate_pr_id"]) for r in await conn.fetch(ROUND1_SQL, ROUND)
        }
        assert judged & expected == subset, "only the author's 30 may already be judged"

        rows = []
        for key, (qn, cn, grade, reason) in zip(keys, grades, strict=True):
            if key in subset:
                continue  # D-V11-5: the author's grade is official
            self_authored = LABELER_LOGIN in (prs[qn]["author"], prs[cn]["author"])
            rows.append((*key, grade, reason, ROUND, V11_BATCH, None, self_authored))

        dist = Counter(r[2] for r in rows)
        print(
            f"grades {len(grades)}; author's skipped {len(subset)}; to insert {len(rows)}  "
            f"(0/1/2: {dist[0]}/{dist[1]}/{dist[2]})"
        )
        if not args.apply:
            print("dry run — nothing written")
            return
        async with conn.transaction():
            await conn.executemany(INSERT_SQL, rows)
        print(f"inserted {len(rows)}")


if __name__ == "__main__":
    asyncio.run(main())
