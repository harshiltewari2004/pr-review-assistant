"""v1.1 candidate pool, D-V11-1 §3. Builds on D-P5-8 without changing it.

Per query (all 40, both cohorts): v1.0's five variants x top POOL_DEPTH,
union the scorer's own top K for every weight setting v1.1 can lock or
report (the tune grid, the holdout baselines, v1.0's locked weights). Using
score.top_k itself, not a re-implementation, is what makes D-P5-9 W3
(unjudged = 0 in every scored top-K) hold by construction: the variants'
evidence filter would otherwise disagree with the scorer on file-only.

A separate module, not an edit to pool.py: score imports pool, so pool
cannot import score; and pool.py built a published v1.0 artifact on a
corpus that no longer exists, so it stays frozen.

Offline only (invariant 13). Never reads grades: only whether a pair has
been judged at all, to count the new pairs labeling must cover.

Usage: python -m eval.pool_v11
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence

from app.retrieval.constants import VECTOR_AGGREGATION
from app.retrieval.scoring import CandidateSet, Weights
from app.retrieval.signals import build_bm25_index
from eval.pool import (
    POOL_DEPTH,
    POOL_PATH,
    REPO_ID,
    VARIANTS,
    build_query_candidates,
    pool_for_query,
)
from eval.score import HOLDOUT_BASELINES, POOL_V11_PATH, QUERIES_V11_SQL, V10_LOCKED, K, top_k
from eval.snapshot import corpus_fingerprint
from eval.tune import weight_grid
from ingest.db import connect

SNAPSHOT_PATH = POOL_PATH.parent / "corpus_snapshot.json"
EXPECTED_QUERIES = {("v1.0", "holdout"): 10, ("v1.0", "tune"): 10, ("v1.1", "holdout"): 20}

JUDGED_SQL = "SELECT DISTINCT query_pr_id, candidate_pr_id FROM judgments"
POOLED_SQL = """
SELECT id, created_at FROM pull_requests
WHERE id = ANY($1::bigint[]) AND in_corpus
"""


def scored_configs() -> list[Weights]:
    """Every weight setting v1.1 can lock or report, first occurrence kept."""
    seen: set[tuple[float, float, float]] = set()
    configs: list[Weights] = []
    for w in (*weight_grid(), *HOLDOUT_BASELINES.values(), V10_LOCKED):
        key = (w.vector, w.file_overlap, w.bm25)
        if key not in seen:
            seen.add(key)
            configs.append(w)
    return configs


def pool_v11_for_query(c: CandidateSet, configs: Sequence[Weights]) -> list[int]:
    """D-P5-8 pool, union the scorer's top K under every config. Sorted by pr_id."""
    pooled = set(pool_for_query(c))
    for w in configs:
        pooled.update(top_k(c, w))
    return sorted(pooled)


async def main() -> None:
    configs = scored_configs()
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    async with connect("local") as conn:
        fingerprint = await corpus_fingerprint(conn, REPO_ID)
        assert fingerprint == snapshot["corpus_fingerprint"], "DB is not the snapshotted corpus"
        index = await build_bm25_index(conn, REPO_ID)
        queries = await conn.fetch(QUERIES_V11_SQL)
        counts: dict[tuple[str, str], int] = {}
        for q in queries:
            counts[(q["cohort"], q["split"])] = counts.get((q["cohort"], q["split"]), 0) + 1
        assert counts == EXPECTED_QUERIES, counts
        judged = {(r["query_pr_id"], r["candidate_pr_id"]) for r in await conn.fetch(JUDGED_SQL)}

        print(f"configs {len(configs)}  aggregation {VECTOR_AGGREGATION}  top {K}")
        entries = []
        new_by_group: dict[tuple[str, str], int] = {}
        for q in queries:
            c = await build_query_candidates(conn, index, q)
            base = pool_for_query(c)
            pool = pool_v11_for_query(c, configs)
            assert set(base) <= set(pool), (q["number"], "v1.0 variants not all pooled")

            # Same guard as pool.py (D-P5-8 §4): assert, never filter. AND in_corpus
            # also proves no PR emptied by the D-V11-1 fix can be pooled.
            found = await conn.fetch(POOLED_SQL, pool)
            assert len(found) == len(pool), (q["number"], "pooled PR missing or out of corpus")
            for r in found:
                assert r["id"] != q["id"], (q["number"], "query pooled itself")
                assert r["created_at"] < q["created_at"], (q["number"], r["id"], "temporal leak")

            new = sum(1 for pr_id in pool if (q["id"], pr_id) not in judged)
            group = (q["cohort"], q["split"])
            new_by_group[group] = new_by_group.get(group, 0) + new
            print(
                f"#{q['number']:<5} {q['cohort']} {q['split']:<7} |C|={len(c.ids):<4} "
                f"variants={len(base):<3} +grid={len(pool) - len(base):<3} "
                f"pool={len(pool):<3} new={new}"
            )
            entries.append(
                {"query_pr_id": q["id"], "query_number": q["number"], "candidate_pr_ids": pool}
            )

        payload = {
            "corpus_fingerprint": fingerprint,
            "pool_depth": POOL_DEPTH,
            "variants": [v.name for v in VARIANTS],
            "top_k": K,
            "configs": len(configs),
            "vector_aggregation": VECTOR_AGGREGATION,
            "queries": entries,
        }
        POOL_V11_PATH.write_text(json.dumps(payload, indent=2) + "\n")

    sizes = sorted(len(e["candidate_pr_ids"]) for e in entries)
    print(
        f"\ntotal pool {sum(sizes)}   per query: min {sizes[0]}, "
        f"median {sizes[len(sizes) // 2]}, max {sizes[-1]}"
    )
    for group in sorted(new_by_group):
        print(f"new pairs  {group[0]} {group[1]:<7} {new_by_group[group]}")
    print(f"new pairs  total        {sum(new_by_group.values())}   -> {POOL_V11_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
