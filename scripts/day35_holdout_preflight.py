"""Day 35: holdout W3 pre-flight (D-P6-2).

Counts unjudged PRs in each holdout top-3 at the LOCKED weights, and nothing
else: it checks only whether a label EXISTS, never reads a grade, and
computes no metric, so no holdout performance is revealed (invariant 14).

Usage: python -m scripts.day35_holdout_preflight
"""

from __future__ import annotations

import asyncio

from app.retrieval.scoring import DEFAULT_WEIGHTS
from eval.score import load_eval_set, top_k
from ingest.db import connect


async def main() -> None:
    async with connect("local") as conn:
        queries = await load_eval_set(conn)
    holdout = [q for q in queries if q.split == "holdout"]
    assert len(holdout) == 10, len(holdout)

    missing = [
        (q.number, c)
        for q in holdout
        for c in top_k(q.candidates, DEFAULT_WEIGHTS)
        if c not in q.labels
    ]
    print(f"holdout top-3 at locked weights: {len(missing)} unjudged of {3 * len(holdout)}")
    for number, pr_id in missing:
        print(f"  query #{number} <- candidate pr_id {pr_id}")


if __name__ == "__main__":
    asyncio.run(main())
