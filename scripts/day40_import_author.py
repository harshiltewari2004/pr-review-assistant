"""Day 40: import the author's 30 (D-V11-5) from query#|candidate#|grade|reason.

Checks the file covers exactly the committed subset, applies label.py's rules
(0/1/2; 1 and 2 need a reason of 1-6 words; a 0 carries none), skips pairs
already judged (counting any that differ; never overwrites, invariant 15),
and inserts the rest as round 1, batch 3 in one transaction. Dry run unless
--apply. Prints counts only, never grades.

Usage:
    python -m scripts.day40_import_author            # dry run
    python -m scripts.day40_import_author --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json

from eval.label import ARTIFACTS, INSERT_SQL, LABELER_LOGIN, MAX_REASON_WORDS, ROUND, V11_BATCH
from ingest.db import connect

REPO_ID = 2
GRADES_PATH = ARTIFACTS / "batch3_author_subset.psv"
SUBSET_PATH = ARTIFACTS / "kappa_subset_v11.json"
PRS_SQL = """
SELECT id, number, author FROM pull_requests
WHERE repo_id = $1 AND number = ANY($2::int[])
"""
EXISTING_SQL = "SELECT query_pr_id, candidate_pr_id, grade FROM judgments WHERE round = $1"


def load_grades(text: str) -> list[tuple[int, int, int, str | None]]:
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        q, c, g, reason = line.split("|", 3)
        grade = int(g)
        reason = reason.strip() or None
        assert grade in (0, 1, 2), f"bad grade: #{q} <- #{c}"
        assert (grade == 0) == (reason is None), f"reason/grade mismatch: #{q} <- #{c}"
        if reason:
            assert len(reason.split()) <= MAX_REASON_WORDS, f"reason > 6 words: #{q} <- #{c}"
        rows.append((int(q), int(c), grade, reason))
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import the author's 30 (D-V11-5)")
    parser.add_argument("--apply", action="store_true", help="write (default: dry run)")
    args = parser.parse_args()

    grades = load_grades(GRADES_PATH.read_text())
    subset = {tuple(p) for p in json.loads(SUBSET_PATH.read_text())}
    numbers = sorted({n for q, c, *_ in grades for n in (q, c)})

    async with connect("local") as conn:
        prs = {r["number"]: r for r in await conn.fetch(PRS_SQL, REPO_ID, numbers)}
        assert len(prs) == len(numbers), "file names a PR number not in the corpus"
        existing = {
            (r["query_pr_id"], r["candidate_pr_id"]): r["grade"]
            for r in await conn.fetch(EXISTING_SQL, ROUND)
        }

        keys = [(prs[q]["id"], prs[c]["id"]) for q, c, *_ in grades]
        assert len(set(keys)) == len(keys), "a pair appears twice"
        assert set(keys) == subset, "file must cover exactly the 30 committed subset pairs"

        rows, same, differ = [], 0, 0
        for key, (qn, cn, grade, reason) in zip(keys, grades, strict=True):
            if key in existing:
                same += existing[key] == grade
                differ += existing[key] != grade
                continue
            self_authored = LABELER_LOGIN in (prs[qn]["author"], prs[cn]["author"])
            rows.append((*key, grade, reason, ROUND, V11_BATCH, None, self_authored))

        print(
            f"parsed {len(grades)}; already judged: {same} same, {differ} differ; "
            f"to insert {len(rows)}"
        )
        if not args.apply:
            print("dry run — nothing written")
            return
        async with conn.transaction():
            await conn.executemany(INSERT_SQL, rows)
        print(f"inserted {len(rows)}")


if __name__ == "__main__":
    asyncio.run(main())
