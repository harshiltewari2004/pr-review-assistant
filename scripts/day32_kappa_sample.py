"""Day 32: draw the blind human-agreement subset from batch 2 (D-P5-14).

3 pairs per batch-2 query (10 queries -> 30), random with a fixed seed, so
the draw is reproducible and fixed in git before anyone labels. Refuses if
batch 2 already has judgments. Writes eval/artifacts/kappa_subset_batch2.json
as [[query_pr_id, candidate_pr_id], ...]. Prints counts only, not the pairs.

Usage: python -m scripts.day32_kappa_sample
"""

from __future__ import annotations

import asyncio
import json
import random

from eval.label import ARTIFACTS, POOL_PATH, QUERIES_SQL, batch_query_ids
from ingest.db import connect

BATCH = 2
PER_QUERY = 3
SEED = 32
OUT_PATH = ARTIFACTS / "kappa_subset_batch2.json"


async def main() -> None:
    pool = {
        e["query_pr_id"]: e["candidate_pr_ids"]
        for e in json.loads(POOL_PATH.read_text())["queries"]
    }

    async with connect("local") as conn:
        qrows = await conn.fetch(QUERIES_SQL)
        done = await conn.fetchval("SELECT count(*) FROM judgments WHERE batch = $1", BATCH)
    assert done == 0, f"batch {BATCH} already has {done} judgments; draw the subset first"

    batch_ids = batch_query_ids(qrows, BATCH)
    assert len(batch_ids) == 10, batch_ids

    rng = random.Random(SEED)
    subset = []
    for q in batch_ids:
        cands = sorted(pool[q])
        assert len(cands) >= PER_QUERY, (q, len(cands))
        subset += [[q, c] for c in sorted(rng.sample(cands, PER_QUERY))]

    assert len(subset) == 10 * PER_QUERY
    OUT_PATH.write_text(json.dumps(subset, indent=2) + "\n")
    print(f"wrote {len(subset)} pairs across {len(batch_ids)} queries to {OUT_PATH.name}")


if __name__ == "__main__":
    asyncio.run(main())
