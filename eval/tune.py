"""Phase 6 tuning on the TUNE split, exactly per D-P6-1 (pre-registered).

66 weight settings on the 0.1 simplex x vector aggregation {max, mean_top_k}.
A config is eligible only with zero unjudged PRs in every tune top-3
(D-P5-9 W3). Winner by lexicographic key: higher lenient R@3, then strict
R@3, then MRR@3 (means over scorable queries, rounded to 6 dp), then smaller
L1 distance to DEFAULT_WEIGHTS, then max before mean_top_k, then grid order.
Holdout queries are never scored (invariant 14). Writes the full grid,
losers included, to eval/artifacts/tune_grid.json.

Usage: python -m eval.tune
"""

from __future__ import annotations

import asyncio
import json
import random

from app.retrieval.scoring import Weights
from eval.pool import POOL_PATH
from eval.score import SEED, load_eval_set, score_split
from ingest.db import connect

AGGREGATIONS = ("max", "mean_top_k")  # order is the D-P6-1 tie-break
GRID_STEPS = 10  # 0.1 simplex -> 66 settings
DECIMALS = 6
OUT_PATH = POOL_PATH.parent / "tune_grid.json"
# The D-P6-1 prior, pinned so a re-run after the lock reproduces this grid (D-P6-2).
PRIOR_WEIGHTS = Weights(vector=0.5, file_overlap=0.3, bm25=0.2)


def weight_grid() -> list[Weights]:
    """Every (vector, file_overlap, bm25) in steps of 1/GRID_STEPS summing to 1."""
    grid = []
    for v in range(GRID_STEPS, -1, -1):
        for f in range(GRID_STEPS - v, -1, -1):
            b = GRID_STEPS - v - f
            grid.append(
                Weights(vector=v / GRID_STEPS, file_overlap=f / GRID_STEPS, bm25=b / GRID_STEPS)
            )
    assert len(grid) == 66, len(grid)
    return grid


def l1_to_default(w: Weights) -> float:
    d = PRIOR_WEIGHTS
    return round(
        abs(w.vector - d.vector) + abs(w.file_overlap - d.file_overlap) + abs(w.bm25 - d.bm25),
        DECIMALS,
    )


def query_mean(per_query: list[dict], name: str) -> float:
    """Mean over scorable queries (None excluded), rounded to DECIMALS. D-P6-1."""
    values = [p[name] for p in per_query if p[name] is not None]
    return round(sum(values) / len(values), DECIMALS)


def selection_key(r: dict) -> tuple:
    """D-P6-1 order: higher metrics first, then nearest default, max, grid order."""
    return (
        -r["recall_lenient"],
        -r["recall_strict"],
        -r["mrr"],
        r["l1_to_default"],
        r["agg_rank"],
        r["grid_rank"],
    )


def _line(r: dict) -> str:
    v, f, b = r["weights"]
    rank = r.get("rank", "-")
    return (
        f"{rank:>4} {r['aggregation']:<10} v={v:.1f} f={f:.1f} b={b:.1f}  "
        f"R@3 {r['recall_lenient']:.4f}  strict {r['recall_strict']:.4f}  "
        f"MRR {r['mrr']:.4f}  L1 {r['l1_to_default']:.1f}  unjudged {r['unjudged']}"
    )


async def main() -> None:
    grid = weight_grid()
    rows = []
    for agg_rank, agg in enumerate(AGGREGATIONS):
        async with connect("local") as conn:
            queries = await load_eval_set(conn, vector_aggregation=agg)
        tune = [q for q in queries if q.split == "tune"]
        assert len(tune) == 10, len(tune)
        for grid_rank, w in enumerate(grid):
            result = score_split(tune, w, random.Random(SEED))
            pq = result["per_query"]
            rows.append(
                {
                    "aggregation": agg,
                    "weights": [w.vector, w.file_overlap, w.bm25],
                    "recall_lenient": query_mean(pq, "recall_lenient"),
                    "recall_strict": query_mean(pq, "recall_strict"),
                    "mrr": query_mean(pq, "mrr_lenient"),
                    "unjudged": result["unjudged_in_top3"],
                    "l1_to_default": l1_to_default(w),
                    "agg_rank": agg_rank,
                    "grid_rank": grid_rank,
                }
            )

    eligible = sorted((r for r in rows if r["unjudged"] == 0), key=selection_key)
    for rank, r in enumerate(eligible, 1):
        r["rank"] = rank
    winner = eligible[0]
    default = next(r for r in rows if r["aggregation"] == "max" and r["weights"] == [0.5, 0.3, 0.2])

    for agg in AGGREGATIONS:
        n = sum(1 for r in rows if r["aggregation"] == agg and r["unjudged"] == 0)
        print(f"{agg:<10} eligible {n}/66")
    top_value = winner["recall_lenient"]
    tied = sum(1 for r in eligible if r["recall_lenient"] == top_value)
    print(f"\ntied at the top lenient R@3 ({top_value:.4f}): {tied}")
    print("\ntop 10 eligible:")
    for r in eligible[:10]:
        print(_line(r))
    print("\ndefault (max, 0.5/0.3/0.2):")
    print(_line(default))
    print("\nWINNER:")
    print(_line(winner))

    OUT_PATH.write_text(
        json.dumps(
            {
                "protocol": "D-P6-1",
                "split": "tune",
                "winner": winner,
                "default_rank": default.get("rank"),
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
