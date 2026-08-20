"""Day 17 — vector similarity query + latency measurement (D-P2-24).

Read-only. Picks the most recent in-corpus PR as the query, pulls its stored
chunk vectors, and runs the vector signal against the corpus.

Not the production path: production embeds the incoming diff at request time.
Reading vectors back isolates the SQL from the model load.
"""

from __future__ import annotations

import asyncio
import sys
import time

from app.retrieval.signals import VECTOR_SIGNAL_SQL, vector_signal
from ingest.db import connect

REPO = "processing/p5.js"
TOP_K = 10


async def main(target: str) -> None:
    async with connect(target) as conn:
        repo_id = await conn.fetchval(
            "SELECT id FROM repos WHERE full_name = $1", REPO
        )
        if repo_id is None:
            sys.exit(f"no repo row for {REPO} on {target}")
        print(f"target={target}  repo_id={repo_id}")

        order = "ASC" if len(sys.argv) > 2 and sys.argv[2] == "mid" else "DESC"
        q = await conn.fetchrow(
            f"""
            SELECT p.id, p.number, p.title, p.created_at
            FROM pull_requests p
            WHERE p.repo_id = $1 AND p.in_corpus
              AND EXISTS (SELECT 1 FROM chunks c WHERE c.pr_id = p.id)
            ORDER BY p.created_at {order}
            OFFSET 1600 LIMIT 1
            """,
            repo_id,
        )
        print(f"query PR #{q['number']} ({q['created_at']:%Y-%m-%d}) {q['title'][:60]}")

        # D-P3-1 consequence: the read path returns pgvector Vector objects.
        rows = await conn.fetch(
            "SELECT embedding FROM chunks WHERE pr_id = $1 ORDER BY id", q["id"]
        )
        vectors = [r["embedding"].to_numpy() for r in rows]
        print(f"query PR has {len(vectors)} chunks\n")

        # --- fan-out: every query chunk, timed ---
        timings = []
        for v in vectors:
            t0 = time.perf_counter()
            results = await vector_signal(
                conn, v, repo_id, q["created_at"], q["id"], top_k=TOP_K
            )
            timings.append((time.perf_counter() - t0) * 1000)

        meta = {
            r["id"]: r
            for r in await conn.fetch(
                "SELECT id, number, title, created_at FROM pull_requests "
                "WHERE id = ANY($1::bigint[])",
                [pr_id for pr_id, _ in results],
            )
        }
        for rank, (pr_id, score) in enumerate(results, 1):
            m = meta[pr_id]
            print(f"{rank:2}. {score:+.4f}  #{m['number']:5}  "
                  f"{m['created_at']:%Y-%m-%d}  {m['title'][:55]}")

        # --- golden assertion: invariant 1 ---
        leaks = [
            meta[pr_id]["number"]
            for pr_id, _ in results
            if meta[pr_id]["created_at"] >= q["created_at"]
        ]
        print(f"\ntemporal filter: {len(results)} results, {len(leaks)} leaks {leaks}")
        assert not leaks, f"TEMPORAL LEAK: {leaks}"
        
        print(f"\nper-chunk ms: {' '.join(f'{t:.0f}' for t in timings)}")
        print(f"first={timings[0]:.1f}  median={sorted(timings)[len(timings) // 2]:.1f}"
              f"  total={sum(timings):.0f} ms for {len(timings)} chunks")

        plan = await conn.fetch(
            "EXPLAIN ANALYZE " + VECTOR_SIGNAL_SQL,
            vectors[0], repo_id, q["created_at"], q["id"], TOP_K,
        )
        print()
        for line in plan:
            print(line[0])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "local"))