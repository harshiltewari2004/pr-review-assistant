"""Candidate pooling across retrieval variants. 01 §9. D-P5-8.

Per query: build C once, rank it under five variants, take each variant's
top POOL_DEPTH, union. Every pooled PR is judged (01 §10), so no later
top-3 can contain an unjudged PR.

Offline only (invariant 13): reads the local snapshot, writes pool.json.
Imports app/; app/ never imports eval/ (invariant 12).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.retrieval.scoring import (
    DEFAULT_WEIGHTS,
    CandidateSet,
    Weights,
    build_backfilled_candidates,
    rank_candidates,
)
from app.retrieval.signals import build_bm25_index, build_document
from ingest.db import connect

POOL_DEPTH = 6  # 01 §9 step 2
REPO_ID = 2
POOL_PATH = Path(__file__).with_name("pool.json")

QUERIES_SQL = """
SELECT p.id, p.number, p.created_at, p.title, p.body, p.files_changed, q.split
FROM eval_queries q JOIN pull_requests p ON p.id = q.pr_id
ORDER BY p.id
"""

_EVIDENCE_FIELDS = {"vector_raw", "file_overlap_raw", "bm25_raw"}


@dataclass(frozen=True, slots=True, kw_only=True)
class Variant:
    """One retrieval variant to pool from. 01 §9 step 1. D-P5-8.

    evidence names the CandidateSet raw dict a single-signal variant needs a
    positive score in. A PR with zero raw evidence (Jaccard 0.0) is not
    retrieved by that signal at all; without this, a degenerate signal pools
    its lowest pr_ids by tie-break. None for hybrid variants.
    """

    name: str
    weights: Weights
    evidence: str | None

    def __post_init__(self) -> None:
        if self.evidence is not None and self.evidence not in _EVIDENCE_FIELDS:
            raise ValueError(f"unknown evidence field {self.evidence!r}")


VARIANTS = (
    Variant(
        name="vector",
        weights=Weights(vector=1.0, file_overlap=0.0, bm25=0.0),
        evidence="vector_raw",
    ),
    Variant(
        name="file_overlap",
        weights=Weights(vector=0.0, file_overlap=1.0, bm25=0.0),
        evidence="file_overlap_raw",
    ),
    Variant(
        name="bm25",
        weights=Weights(vector=0.0, file_overlap=0.0, bm25=1.0),
        evidence="bm25_raw",
    ),
    Variant(name="hybrid_default", weights=DEFAULT_WEIGHTS, evidence=None),
    Variant(
        name="hybrid_equal",
        weights=Weights(vector=1 / 3, file_overlap=1 / 3, bm25=1 / 3),
        evidence=None,
    ),
)


def variant_picks(candidates: CandidateSet) -> dict[str, list[int]]:
    """Each variant's top POOL_DEPTH pr_ids over one C, best first. 01 §9 steps 1-2.

    Every variant ranks ALL of C, then filters for evidence, then cuts.
    For a single-signal variant zero raw sorts last, so cut-then-filter
    would give the same result; filter-first is defensive, not load-bearing.

    Order and variant names are for terminal diagnostics only; they never
    reach pool.json (blindness, 02 §7, D-P5-8).
    """
    picks: dict[str, list[int]] = {}
    for variant in VARIANTS:
        ranked = rank_candidates(candidates, weights=variant.weights, top_n=len(candidates.ids))
        if variant.evidence is not None:
            raw = getattr(candidates, variant.evidence)
            ranked = [r for r in ranked if raw[r.pr_id] > 0.0]
        picks[variant.name] = [r.pr_id for r in ranked[:POOL_DEPTH]]
    return picks


def pool_for_query(candidates: CandidateSet) -> list[int]:
    """Union of every variant's picks, sorted by pr_id. 01 §9 step 4.

    Pure: the same C always gives the same pool, which is what makes the
    golden assertion (two runs, byte-identical pool.json) possible. Sorted
    ascending so no rank order leaks into labeling.
    """
    pooled: set[int] = set()
    for ids in variant_picks(candidates).values():
        pooled.update(ids)
    return sorted(pooled)


async def main() -> None:
    async with connect("local") as conn:
        index = await build_bm25_index(conn, REPO_ID)
        queries = await conn.fetch(QUERIES_SQL)
        assert len(queries) == 20, f"expected 20 eval queries, got {len(queries)}"

        entries = []
        for q in queries:
            rows = await conn.fetch(
                "SELECT embedding FROM chunks WHERE pr_id = $1 ORDER BY file_path, hunk_index",
                q["id"],
            )
            embeddings = [r["embedding"].to_numpy().astype(np.float32) for r in rows]
            tokens = build_document(q["title"], q["body"], q["files_changed"])

            c = await build_backfilled_candidates(
                conn,
                index,
                repo_id=REPO_ID,
                query_pr_id=q["id"],
                query_created_at=q["created_at"],
                query_embeddings=embeddings,
                query_files=q["files_changed"],
                query_tokens=tokens,
            )
            picks = variant_picks(c)
            pool = pool_for_query(c)
            assert set(pool) == set().union(*picks.values()), q["number"]

            # 01 §9 step 3: ASSERT, never filter (D-P5-8 §4). A filter here
            # would silently drop a leaked PR and hide a signal bug.
            found = await conn.fetch(
                "SELECT id, created_at FROM pull_requests WHERE id = ANY($1::bigint[])", pool
            )
            assert len(found) == len(pool), (q["number"], len(found), len(pool))
            for r in found:
                assert r["id"] != q["id"], (q["number"], "query pooled itself")
                assert r["created_at"] < q["created_at"], (q["number"], r["id"], "temporal leak")

            counts = " ".join(f"{name}={len(ids)}" for name, ids in picks.items())
            print(
                f"#{q['number']:<5} {q['split']:<7} |C|={len(c.ids):<4} "
                f"pool={len(pool):<3} {counts}"
            )
            entries.append(
                {"query_pr_id": q["id"], "query_number": q["number"], "candidate_pr_ids": pool}
            )

        payload = {
            "pool_depth": POOL_DEPTH,
            "variants": [v.name for v in VARIANTS],
            "queries": entries,
        }
        POOL_PATH.write_text(json.dumps(payload, indent=2) + "\n")

        sizes = sorted(len(e["candidate_pr_ids"]) for e in entries)
        print(
            f"\ntotal to judge: {sum(sizes)}   per query: min {sizes[0]}, "
            f"median {sizes[len(sizes) // 2]}, max {sizes[-1]}   -> {POOL_PATH}"
        )


if __name__ == "__main__":
    asyncio.run(main())
