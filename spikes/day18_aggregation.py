"""Day 18 — chunk to PR aggregation across query chunks (03 §5).

Read-only. Closes the Day 17 open loop: that spike printed the LAST query
chunk's ranking because `results` was rebound each iteration. This one
aggregates all of them.

Not the production path: production embeds the incoming diff at request time.
Reading stored vectors back isolates aggregation from model load, so the
timings below EXCLUDE embedding cost and must not be quoted as end-to-end.

Uses the production VECTOR_TOP_K, not Day 17's display TOP_K of 10 — union
size and the max/mean comparison both depend on per-chunk list depth.

    python -m spikes.day18_aggregation local [pr_number]
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections import Counter, defaultdict

from app.retrieval.constants import VECTOR_TOP_K
from app.retrieval.signals import aggregate_chunk_scores, vector_signal, vector_signal_for_pr
from ingest.db import connect

REPO = "processing/p5.js"
DEFAULT_QUERY_PR = 9032
WATCH_PR = 4132  # "Test pr" (2019, throwaway) — scored 0.70 on one chunk, Day 17
SHOW = 10


async def main(target: str, pr_number: int) -> None:
    async with connect(target) as conn:
        repo_id = await conn.fetchval("SELECT id FROM repos WHERE full_name = $1", REPO)
        if repo_id is None:
            sys.exit(f"no repo row for {REPO} on {target}")

        q = await conn.fetchrow(
            "SELECT id, number, title, created_at FROM pull_requests "
            "WHERE repo_id = $1 AND number = $2",
            repo_id,
            pr_number,
        )
        if q is None:
            sys.exit(f"PR #{pr_number} not found on {target}")
        print(f"target={target}  repo_id={repo_id}  VECTOR_TOP_K={VECTOR_TOP_K}")
        print(f"query PR #{q['number']} ({q['created_at']:%Y-%m-%d}) {q['title'][:60]}")

        rows = await conn.fetch(
            "SELECT embedding FROM chunks WHERE pr_id = $1 ORDER BY id", q["id"]
        )
        vectors = [r["embedding"].to_numpy() for r in rows]
        print(f"query PR has {len(vectors)} chunks\n")

        # --- aggregate, MAX ---
        t0 = time.perf_counter()
        agg_max = await vector_signal_for_pr(
            conn, vectors, repo_id, q["created_at"], q["id"], strategy="max"
        )
        wall_max = (time.perf_counter() - t0) * 1000

        # --- aggregate, mean-of-top-3 ---
        agg_mean = await vector_signal_for_pr(
            conn, vectors, repo_id, q["created_at"], q["id"], strategy="mean_top_k"
        )

        print(f"union across {len(vectors)} chunks: {len(agg_max)} distinct candidates")
        print(f"ceiling if disjoint: {len(vectors) * VECTOR_TOP_K}")
        print(f"fan-out wall clock: {wall_max:.0f} ms (excludes embedding)\n")

        # --- metadata for everything in the union, one query (06 §9) ---
        meta = {
            r["id"]: r
            for r in await conn.fetch(
                "SELECT id, number, title, created_at FROM pull_requests "
                "WHERE id = ANY($1::bigint[])",
                list(agg_max),
            )
        }

        def ranked(agg):
            return sorted(agg.items(), key=lambda kv: (-kv[1].score_raw, kv[0]))

        top_max = ranked(agg_max)
        top_mean = ranked(agg_mean)

        print(f"top {SHOW} by MAX:")
        for rank, (pr_id, a) in enumerate(top_max[:SHOW], 1):
            m = meta[pr_id]
            print(
                f"{rank:2}. {a.score_raw:+.4f}  hits={a.chunk_hits:2}  #{m['number']:5}  "
                f"{m['created_at']:%Y-%m-%d}  {m['title'][:50]}"
            )

        print(f"\ntop {SHOW} by MEAN_TOP_K:")
        for rank, (pr_id, a) in enumerate(top_mean[:SHOW], 1):
            m = meta[pr_id]
            print(
                f"{rank:2}. {a.score_raw:+.4f}  hits={a.chunk_hits:2}  #{m['number']:5}  "
                f"{m['created_at']:%Y-%m-%d}  {m['title'][:50]}"
            )

        # --- prediction 1: does the throwaway survive aggregation? ---
        watch = [
            (rank, a)
            for rank, (pr_id, a) in enumerate(top_max, 1)
            if meta[pr_id]["number"] == WATCH_PR
        ]
        if watch:
            rank, a = watch[0]
            print(f"\n#{WATCH_PR}: rank {rank} of {len(top_max)}, "
                  f"score {a.score_raw:.4f}, hits {a.chunk_hits}")
        else:
            print(f"\n#{WATCH_PR}: not in the union")

        # --- prediction 4: do the two strategies actually differ here? ---
        ids_max = {pr_id for pr_id, _ in top_max[:SHOW]}
        ids_mean = {pr_id for pr_id, _ in top_mean[:SHOW]}
        print(f"top-{SHOW} overlap max vs mean: {len(ids_max & ids_mean)}/{SHOW}")

        # --- D-P6-1: ties ---
        scores = [round(a.score_raw, 6) for _, a in top_max[:SHOW]]
        print(f"distinct scores in top {SHOW}: {len(set(scores))}/{SHOW}")

        # --- chunk_hits distribution: how much cutoff bias is in play ---
        hits = Counter(a.chunk_hits for a in agg_max.values())
        print(f"chunk_hits: seen once={hits[1]}  all {len(vectors)}={hits[len(vectors)]}  "
              f"max observed={max(hits)}")

        # --- GOLDEN ASSERTION 1: invariant 1, over the FULL union ---
        leaks = [
            meta[pr_id]["number"]
            for pr_id in agg_max
            if meta[pr_id]["created_at"] >= q["created_at"]
        ]
        print(f"\ntemporal filter: {len(agg_max)} candidates, {len(leaks)} leaks {leaks}")
        assert not leaks, f"TEMPORAL LEAK: {leaks}"

        # --- GOLDEN ASSERTION 2: order independence on real data ---
        agg_rev = await vector_signal_for_pr(
            conn, list(reversed(vectors)), repo_id, q["created_at"], q["id"], strategy="max"
        )
        assert agg_rev == agg_max, "MAX aggregation is order-dependent"
        print("order independence: reversed chunk order gives an identical map")

        # --- GOLDEN ASSERTION 3: independent recomputation of the wiring ---
        collected: dict[int, list[float]] = defaultdict(list)
        for v in vectors:
            for pr_id, score_raw in await vector_signal(
                conn, v, repo_id, q["created_at"], q["id"]
            ):
                collected[pr_id].append(score_raw)
        assert aggregate_chunk_scores(dict(collected)) == agg_max, "orchestrator wiring drift"
        print("recomputed from raw rows: identical")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "local"
    number = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_QUERY_PR
    asyncio.run(main(target, number))