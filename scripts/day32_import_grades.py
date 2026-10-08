"""Day 32: import Claude-proposed batch-1 grades (D-P5-13).

Reads eval/artifacts/batch1_claude_grades.psv (query#|candidate#|grade|reason),
checks it covers exactly the batch-1 pool pairs, skips pairs already judged in
round 1 (reporting any whose grade/reason differs; never overwrites, invariant
15), and inserts the rest in one transaction. Dry run unless --apply.

Usage:
    python -m scripts.day32_import_grades           # dry run
    python -m scripts.day32_import_grades --apply   # write
"""

from __future__ import annotations

import argparse
import asyncio
import json

from eval.label import (
    ARTIFACTS,
    INSERT_SQL,
    LABELER_LOGIN,
    MAX_REASON_WORDS,
    POOL_PATH,
    QUERIES_SQL,
    ROUND,
    batch_query_ids,
)
from ingest.db import connect

BATCH = 1
REPO_ID = 2
GRADES_PATH = ARTIFACTS / "batch1_claude_grades.psv"

PRS_BY_NUMBER_SQL = """
SELECT id, number, author FROM pull_requests
WHERE repo_id = $1 AND number = ANY($2::int[])
"""
EXISTING_SQL = """
SELECT query_pr_id, candidate_pr_id, grade, reason FROM judgments WHERE round = $1
"""


def load_grades(text: str) -> list[tuple[int, int, int, str | None]]:
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        q, c, g, reason = line.split("|", 3)
        grade = int(g)
        reason = reason.strip() or None
        assert grade in (0, 1, 2), line
        assert (grade == 0) == (reason is None), f"reason/grade mismatch: {line}"
        if reason:
            assert len(reason.split()) <= MAX_REASON_WORDS, f"reason too long: {line}"
        rows.append((int(q), int(c), grade, reason))
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write (default: dry run)")
    args = parser.parse_args()

    grades = load_grades(GRADES_PATH.read_text())
    pool = {
        e["query_pr_id"]: e["candidate_pr_ids"]
        for e in json.loads(POOL_PATH.read_text())["queries"]
    }

    async with connect("local") as conn:
        qrows = await conn.fetch(QUERIES_SQL)
        batch_ids = batch_query_ids(qrows, BATCH)
        expected = {(q, c) for q in batch_ids for c in pool[q]}

        numbers = {n for q, c, _, _ in grades for n in (q, c)}
        prs = await conn.fetch(PRS_BY_NUMBER_SQL, REPO_ID, list(numbers))
        by_num = {r["number"]: r for r in prs}
        assert len(by_num) == len(numbers), f"unknown PR numbers: {numbers - set(by_num)}"
        num_of = {r["id"]: r["number"] for r in prs}

        pairs = {}
        for q, c, grade, reason in grades:
            key = (by_num[q]["id"], by_num[c]["id"])
            assert key not in pairs, f"duplicate pair #{q} <- #{c}"
            self_authored = LABELER_LOGIN in (by_num[q]["author"], by_num[c]["author"])
            pairs[key] = (grade, reason, self_authored)

        missing, extra = expected - set(pairs), set(pairs) - expected
        assert not missing and not extra, (
            f"missing {[(num_of.get(q), num_of.get(c)) for q, c in missing]}, "
            f"extra {[(num_of[q], num_of[c]) for q, c in extra]}"
        )

        existing = {
            (r["query_pr_id"], r["candidate_pr_id"]): (r["grade"], r["reason"])
            for r in await conn.fetch(EXISTING_SQL, ROUND)
        }
        mismatches, to_insert = [], []
        for key, (grade, reason, self_authored) in sorted(pairs.items()):
            if key in existing:
                if existing[key] != (grade, reason):
                    mismatches.append(
                        (num_of[key[0]], num_of[key[1]], existing[key], (grade, reason))
                    )
                continue
            to_insert.append((*key, grade, reason, self_authored))

        print(f"file pairs: {len(pairs)} (batch {BATCH} pool: {len(expected)})")
        print(f"already judged: {len(pairs) - len(to_insert)}  to insert: {len(to_insert)}")
        print(f"mismatches with saved rows: {len(mismatches)}")
        for q, c, saved, proposed in mismatches:
            print(f"  #{q} <- #{c}: saved {saved!r} vs file {proposed!r}")

        if not args.apply:
            print("dry run — nothing written")
            return

        async with conn.transaction():
            for q, c, grade, reason, self_authored in to_insert:
                await conn.execute(
                    INSERT_SQL, q, c, grade, reason, ROUND, BATCH, None, self_authored
                )
        print(f"inserted {len(to_insert)}")


if __name__ == "__main__":
    asyncio.run(main())
