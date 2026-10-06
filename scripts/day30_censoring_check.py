"""Day 30: does censored vector nomination drop any global vector top-6 PR from C?

D-P4-14 open item. Inside C, vector_raw is the uncensored backfill score, so
within-C top-6 == global top-6 iff every global top-6 PR is in C. Global
scores reuse vector_backfill_for_pr over ALL past in-corpus PRs: same
function, same filters (VECTOR_BACKFILL_SQL), so the comparison is like-for-like.

Decides pool.py's vector-only variant: zero misses -> rank within C; any
miss -> query globally (a missed PR is never pooled, so Recall@3 inflates).
The pool only ever runs on these 20 queries, so this is exhaustive, not a sample.
"""

from __future__ import annotations

import asyncio
import math

import numpy as np

from app.retrieval.scoring import _nominate, build_backfilled_candidates
from app.retrieval.signals import build_bm25_index, build_document, vector_backfill_for_pr
from ingest.db import connect

REPO_ID = 2
POOL_DEPTH = 6  # 01 §9: top-6 per variant

QUERIES_SQL = """
SELECT p.id, p.number, p.created_at, p.title, p.body, p.files_changed,
       q.split, q.subsystem
FROM eval_queries q JOIN pull_requests p ON p.id = q.pr_id
ORDER BY q.split, q.subsystem, p.number
"""

PAST_IDS_SQL = """
SELECT id FROM pull_requests
WHERE repo_id = $1 AND in_corpus AND created_at < $2 AND id <> $3
"""


async def main() -> None:
    async with connect("local") as conn:
        index = await build_bm25_index(conn, REPO_ID)
        queries = await conn.fetch(QUERIES_SQL)
        assert len(queries) == 20, f"expected 20 eval queries, got {len(queries)}"

        affected = 0
        total_missing = 0
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

            past = [
                r["id"] for r in await conn.fetch(PAST_IDS_SQL, REPO_ID, q["created_at"], q["id"])
            ]
            full = await vector_backfill_for_pr(
                conn, embeddings, REPO_ID, q["created_at"], q["id"], candidate_ids=past
            )
            global_raw = {i: a.score_raw for i, a in full.items()}

            # Like-for-like: the same function must score a C member identically
            # whether C or the whole past was passed as candidate_ids.
            for i in c.ids:
                assert math.isclose(c.vector_raw[i], global_raw[i], abs_tol=1e-6), (
                    q["number"],
                    i,
                    c.vector_raw[i],
                    global_raw[i],
                )

            global_top = _nominate(global_raw, POOL_DEPTH)
            within_top = _nominate(c.vector_raw, POOL_DEPTH)
            in_c = set(c.ids)
            missing = [i for i in global_top if i not in in_c]

            label = (
                f"#{q['number']:<5} {q['split']:<7} {q['subsystem']:<10} "
                f"|C|={len(c.ids):<4} past={len(past):<5}"
            )
            if not missing:
                assert within_top == global_top, (q["number"], within_top, global_top)
                print(f"{label} global top-{POOL_DEPTH} in C: {POOL_DEPTH}/{POOL_DEPTH}  OK")
                continue

            affected += 1
            total_missing += len(missing)
            numbers = {
                r["id"]: r["number"]
                for r in await conn.fetch(
                    "SELECT id, number FROM pull_requests WHERE id = ANY($1::bigint[])", missing
                )
            }
            details = ", ".join(
                f"#{numbers[i]} (global rank {global_top.index(i) + 1}, {global_raw[i]:.4f})"
                for i in missing
            )
            print(f"{label} MISS {len(missing)}: {details}")

        print(f"\nqueries affected: {affected}/20   missing PRs: {total_missing}/{20 * POOL_DEPTH}")


if __name__ == "__main__":
    asyncio.run(main())
