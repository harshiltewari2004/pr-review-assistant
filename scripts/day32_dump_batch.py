"""Day 32: dump a batch in label.py's exact blind display (D-P5-13).

Reuses label.py's render(), pool, and batch composition, so the grader sees
exactly what the labeling CLI shows: no score, rank, variant, or author; the
query's outcome hidden. Fixed pool order (not shuffled). Read-only.

Usage: python -m scripts.day32_dump_batch --batch 1 > /tmp/batch1.txt
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from eval.label import POOL_PATH, PR_SQL, QUERIES_SQL, batch_query_ids, render
from ingest.db import connect


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=(1, 2), required=True)
    parser.add_argument("--pairs", type=Path, help="dump only these pairs (D-P5-14 subset)")
    args = parser.parse_args()

    pool = {
        e["query_pr_id"]: e["candidate_pr_ids"]
        for e in json.loads(POOL_PATH.read_text())["queries"]
    }

    async with connect("local") as conn:
        qrows = await conn.fetch(QUERIES_SQL)
        batch_ids = batch_query_ids(qrows, args.batch)
        assert len(batch_ids) == 10, batch_ids
        if args.pairs:
            subset = {tuple(p) for p in json.loads(args.pairs.read_text())}
            pool = {q: [c for c in pool[q] if (q, c) in subset] for q in batch_ids}

        all_ids = set(batch_ids) | {c for q in batch_ids for c in pool[q]}
        prs = {r["id"]: r for r in await conn.fetch(PR_SQL, list(all_ids))}
        assert len(prs) == len(all_ids), "pool references a missing PR"

        n = 0
        for qi, q in enumerate(batch_ids, 1):
            print("=" * 78)
            print(f"QUERY {qi}/10\n" + render(prs[q], "QUERY", show_outcome=False))
            for ci, c in enumerate(pool[q], 1):
                n += 1
                print("-" * 78)
                print(
                    f"pair {n}: query #{prs[q]['number']} <- candidate "
                    f"#{prs[c]['number']} ({ci}/{len(pool[q])})"
                )
                print(render(prs[c], "CANDIDATE", show_outcome=True))

        print(f"\n{n} pairs")
        assert n in (170, 175) or args.pairs, n


if __name__ == "__main__":
    asyncio.run(main())
