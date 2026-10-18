"""Day 40: draw the blind human-agreement subset for v1.1 (D-V11-1 §4, D-V11-5).

30 pairs from the v1.1 holdout's never-judged pairs: one per query (20),
plus a second from 10 queries chosen by the same seeded generator, so every
holdout query gets a human check. Fixed seed, committed before anyone
labels. Refuses if batch 3 already has judgments. Writes
eval/artifacts/kappa_subset_v11.json as [[query_pr_id, candidate_pr_id], ...].
Prints counts only, not the pairs.

Usage: python -m scripts.day40_kappa_sample
"""

from __future__ import annotations

import asyncio
import json
import random

from eval.label import ARTIFACTS, POOL_V11_PATH, V11_BATCH
from ingest.db import connect

SEED = 33  # D-V11-1 §4
EXTRA_QUERIES = 10  # 20 queries x 1, plus 10 x 1 more = 30
OUT_PATH = ARTIFACTS / "kappa_subset_v11.json"


async def main() -> None:
    pool = {
        e["query_pr_id"]: e["candidate_pr_ids"]
        for e in json.loads(POOL_V11_PATH.read_text())["queries"]
    }
    async with connect("local") as conn:
        done = await conn.fetchval("SELECT count(*) FROM judgments WHERE batch = $1", V11_BATCH)
        assert done == 0, f"batch {V11_BATCH} already has {done} judgments; draw the subset first"
        rows = await conn.fetch("SELECT pr_id FROM eval_queries WHERE cohort = 'v1.1'")
        judged = {
            (r["query_pr_id"], r["candidate_pr_id"])
            for r in await conn.fetch("SELECT query_pr_id, candidate_pr_id FROM judgments")
        }
    queries = sorted(r["pr_id"] for r in rows)
    assert len(queries) == 20, len(queries)

    rng = random.Random(SEED)
    fresh = {q: sorted(c for c in pool[q] if (q, c) not in judged) for q in queries}
    assert all(len(fresh[q]) >= 2 for q in queries), "a query has fewer than 2 new pairs"
    first = {q: rng.choice(fresh[q]) for q in queries}
    subset = [[q, first[q]] for q in queries]
    for q in sorted(rng.sample(queries, EXTRA_QUERIES)):
        subset.append([q, rng.choice([c for c in fresh[q] if c != first[q]])])

    subset.sort()
    assert len({tuple(p) for p in subset}) == 30, "duplicate pair drawn"
    OUT_PATH.write_text(json.dumps(subset, indent=2) + "\n")
    covered = len({q for q, _ in subset})
    print(f"wrote {len(subset)} pairs across {covered} queries to {OUT_PATH.name}")


if __name__ == "__main__":
    asyncio.run(main())
