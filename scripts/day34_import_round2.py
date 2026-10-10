"""Day 34: import round-2 re-grades (D-P5-15).

Reads eval/artifacts/round2_claude_grades.psv (query#|candidate#|grade|reason)
and the manifest eval/artifacts/regrade_round2_pairs.json written by
scripts.day34_dump_regrade. Checks the file covers exactly the manifest's
pairs, then inserts round-2 rows for the "regrade" pairs only. The "measure"
pairs (the author's 30) are never written: their official label stays the
author's round-1 grade. Round 1 is untouched (invariant 15). Prints how
grades moved from round 1 to round 2. Dry run unless --apply.

Usage:
    python -m scripts.day34_import_round2           # dry run
    python -m scripts.day34_import_round2 --apply   # write
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter

from eval.label import ARTIFACTS, INSERT_SQL, LABELER_LOGIN
from ingest.db import connect
from scripts.day32_import_grades import PRS_BY_NUMBER_SQL, REPO_ID, load_grades

ROUND = 2
GRADES_PATH = ARTIFACTS / "round2_claude_grades.psv"
MANIFEST_PATH = ARTIFACTS / "regrade_round2_pairs.json"

ROUND1_SQL = "SELECT query_pr_id, candidate_pr_id, grade FROM judgments WHERE round = 1"
ROUND2_COUNT_SQL = "SELECT count(*) FROM judgments WHERE round = 2"


def moves_to_zero(moves: Counter[tuple[int, int]]) -> int:
    return sum(count for (_, new), count in moves.items() if new == 0)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write (default: dry run)")
    args = parser.parse_args()

    grades = load_grades(GRADES_PATH.read_text())
    manifest = {
        (q, c): (batch, kind) for q, c, batch, kind in json.loads(MANIFEST_PATH.read_text())
    }

    async with connect("local") as conn:
        numbers = {n for q, c, _, _ in grades for n in (q, c)}
        prs = await conn.fetch(PRS_BY_NUMBER_SQL, REPO_ID, list(numbers))
        by_num = {r["number"]: r for r in prs}
        assert len(by_num) == len(numbers), f"unknown PR numbers: {numbers - set(by_num)}"

        file_pairs = {}
        for q, c, grade, reason in grades:
            key = (by_num[q]["id"], by_num[c]["id"])
            assert key not in file_pairs, f"duplicate pair #{q} <- #{c}"
            authors = (by_num[q]["author"], by_num[c]["author"])
            file_pairs[key] = (grade, reason, LABELER_LOGIN in authors)

        missing = set(manifest) - set(file_pairs)
        extra = set(file_pairs) - set(manifest)
        assert not missing and not extra, f"missing {len(missing)}, extra {len(extra)}"

        round1 = {
            (r["query_pr_id"], r["candidate_pr_id"]): r["grade"]
            for r in await conn.fetch(ROUND1_SQL)
        }
        moves: Counter[tuple[int, int]] = Counter()
        to_insert = []
        for key, (grade, reason, self_authored) in sorted(file_pairs.items()):
            batch, kind = manifest[key]
            if kind != "regrade":
                continue
            moves[(round1[key], grade)] += 1
            if grade == 0:
                continue  # D-P5-16: only the 1/2 line moves; the round-1 grade stands
            to_insert.append((*key, grade, reason, ROUND, batch, None, self_authored))

        kinds = Counter(kind for _, kind in manifest.values())
        print(
            f"file pairs: {len(file_pairs)}  regrade: {kinds['regrade']}  "
            f"measure: {kinds['measure']} (never written)"
        )
        print("round 1 -> round 2, regrade set only:")
        for (old, new), count in sorted(moves.items()):
            print(f"  {old} -> {new}: {count}")

        print(f"to insert: {len(to_insert)}  rejected round-2 zeros: {moves_to_zero(moves)}")
        if not args.apply:
            print("dry run — nothing written")
            return

        assert await conn.fetchval(ROUND2_COUNT_SQL) == 0, "round 2 already has rows"
        async with conn.transaction():
            for row in to_insert:
                await conn.execute(INSERT_SQL, *row)
        print(f"inserted {len(to_insert)} round-2 rows")


if __name__ == "__main__":
    asyncio.run(main())
