"""Offline scorer. 01 §11, §13, §14. D-P5-9 W2/W3, D-P5-15, D-P5-16.

Recall@3 (lenient = headline, strict = secondary) and MRR@3 per split,
each with a bootstrap 95% CI over queries, plus per-query ceilings and the
|relevant| distribution. Reads OFFICIAL labels (latest round per pair).
Refuses on corpus fingerprint mismatch; counts unjudged top-3 results.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass

from app.retrieval.scoring import DEFAULT_WEIGHTS, CandidateSet, Weights, rank_candidates
from app.retrieval.signals import build_bm25_index
from eval.pool import POOL_PATH, QUERIES_SQL, REPO_ID, build_query_candidates
from eval.snapshot import corpus_fingerprint
from ingest.db import connect

K = 3
BOOTSTRAP_ROUNDS = 1_000  # 01 §14
SEED = 32
LENIENT_MIN_GRADE = 1
STRICT_MIN_GRADE = 2


def recall_at_k(ranked: Sequence[int], relevant: set[int], k: int = K) -> float | None:
    """Fraction of relevant candidates found in the top k. None if nothing is relevant."""
    if not relevant:
        return None
    hits = sum(1 for c in ranked[:k] if c in relevant)
    return hits / len(relevant)


def recall_ceiling(relevant: set[int], k: int = K) -> float | None:
    """Best possible Recall@k for this query: min(1, k / |relevant|). 01 §11."""
    if not relevant:
        return None
    return min(1.0, k / len(relevant))


def reciprocal_rank(ranked: Sequence[int], relevant: set[int], k: int = K) -> float | None:
    """1 / rank of the first relevant candidate in the top k; 0.0 if none there."""
    if not relevant:
        return None
    for rank, c in enumerate(ranked[:k], start=1):
        if c in relevant:
            return 1.0 / rank
    return 0.0


def bootstrap_ci(
    values: Sequence[float], rng: random.Random, rounds: int = BOOTSTRAP_ROUNDS
) -> tuple[float, float]:
    """Percentile 95% CI of the mean, resampling QUERIES with replacement. 01 §14."""
    n = len(values)
    means = []
    for _ in range(rounds):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    return means[int(0.025 * rounds)], means[int(0.975 * rounds) - 1]


OFFICIAL_LABELS_SQL = """
SELECT DISTINCT ON (query_pr_id, candidate_pr_id) query_pr_id, candidate_pr_id, grade
FROM judgments
ORDER BY query_pr_id, candidate_pr_id, round DESC
"""


@dataclass(frozen=True, slots=True)
class EvalQuery:
    """One eval query: its candidate set C and official labels. D-P5-16."""

    pr_id: int
    number: int
    split: str
    candidates: CandidateSet
    labels: dict[int, int]


async def load_eval_set(conn) -> list[EvalQuery]:
    """All 20 eval queries, C built exactly as pooled, plus official labels.

    Refuses on corpus fingerprint mismatch (D-P5-9 W2): the labels judge the
    pool, the pool came from one corpus, and a changed corpus makes them stale.
    """
    pool = json.loads(POOL_PATH.read_text())
    live = await corpus_fingerprint(conn, REPO_ID)
    if live != pool["corpus_fingerprint"]:
        raise SystemExit(
            f"refusing: corpus fingerprint {live[:8]} != pool {pool['corpus_fingerprint'][:8]}"
            " (D-P5-9 W2)"
        )

    labels: dict[int, dict[int, int]] = {}
    for r in await conn.fetch(OFFICIAL_LABELS_SQL):
        labels.setdefault(r["query_pr_id"], {})[r["candidate_pr_id"]] = r["grade"]

    pooled = {e["query_pr_id"]: set(e["candidate_pr_ids"]) for e in pool["queries"]}
    index = await build_bm25_index(conn, REPO_ID)
    out = []
    for q in await conn.fetch(QUERIES_SQL):
        judged = set(labels.get(q["id"], {}))
        assert judged == pooled[q["id"]], (q["number"], "labels do not match the pool")
        c = await build_query_candidates(conn, index, q)
        out.append(
            EvalQuery(
                pr_id=q["id"],
                number=q["number"],
                split=q["split"],
                candidates=c,
                labels=labels[q["id"]],
            )
        )
    assert len(out) == 20, len(out)
    return out


def relevant(labels: dict[int, int], min_grade: int) -> set[int]:
    """Candidates whose official grade meets the threshold (1 lenient, 2 strict)."""
    return {c for c, g in labels.items() if g >= min_grade}


def top_k(c: CandidateSet, weights: Weights, k: int = K) -> list[int]:
    """The system's top k pr_ids for one query at these weights, best first."""
    return [r.pr_id for r in rank_candidates(c, weights=weights, top_n=k)]


HOLDOUT_LOCK_PATH = POOL_PATH.parent / "holdout_scored.json"
METRIC_NAMES = (
    "recall_lenient",
    "recall_strict",
    "mrr_lenient",
    "ceiling_lenient",
    "ceiling_strict",
)


def summarize(values: list[float | None], rng: random.Random) -> dict:
    """Mean and bootstrap CI over scorable queries. None = unscorable, excluded and counted."""
    scored = [v for v in values if v is not None]
    if not scored:
        return {"mean": None, "ci95": None, "n": 0, "excluded": len(values)}
    lo, hi = bootstrap_ci(scored, rng)
    return {
        "mean": round(sum(scored) / len(scored), 4),
        "ci95": [round(lo, 4), round(hi, 4)],
        "n": len(scored),
        "excluded": len(values) - len(scored),
    }


def score_split(queries: list[EvalQuery], weights: Weights, rng: random.Random) -> dict:
    """Recall@3 (lenient, strict), MRR@3 and ceilings for one split. 01 §11, §14.

    An unjudged PR in a top 3 counts as not relevant (conservative) and is
    counted in unjudged_in_top3 (D-P5-9 W3: must be 0 for a reported number).
    """
    columns: dict[str, list[float | None]] = {name: [] for name in METRIC_NAMES}
    per_query = []
    unjudged = 0
    for q in queries:
        ranked = top_k(q.candidates, weights)
        unjudged += sum(1 for c in ranked if c not in q.labels)
        lenient = relevant(q.labels, LENIENT_MIN_GRADE)
        strict = relevant(q.labels, STRICT_MIN_GRADE)
        row = {
            "recall_lenient": recall_at_k(ranked, lenient),
            "recall_strict": recall_at_k(ranked, strict),
            "mrr_lenient": reciprocal_rank(ranked, lenient),
            "ceiling_lenient": recall_ceiling(lenient),
            "ceiling_strict": recall_ceiling(strict),
        }
        for name, value in row.items():
            columns[name].append(value)
        per_query.append(
            {"query": q.number, "relevant_lenient": len(lenient), "relevant_strict": len(strict)}
            | row
        )
    return {
        "n_queries": len(queries),
        "unjudged_in_top3": unjudged,
        "metrics": {name: summarize(values, rng) for name, values in columns.items()},
        "relevant_lenient_sizes": sorted(p["relevant_lenient"] for p in per_query),
        "per_query": per_query,
    }


def parse_weights(text: str) -> Weights:
    """'0.5,0.3,0.2' -> Weights(vector, file_overlap, bm25). Weights validates the sum."""
    v, f, b = (float(x) for x in text.split(","))
    return Weights(vector=v, file_overlap=f, bm25=b)


def _fmt(value: float | None) -> str:
    return "  -  " if value is None else f"{value:.2f}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Offline scorer (01 §11, §14)")
    parser.add_argument("--split", choices=("tune", "holdout"), default="tune")
    parser.add_argument("--weights", type=parse_weights, default=DEFAULT_WEIGHTS)
    parser.add_argument("--holdout-once", action="store_true", help="invariant 14")
    args = parser.parse_args()

    if args.split == "holdout":
        if not args.holdout_once:
            raise SystemExit("holdout needs --holdout-once: it is scored exactly once (inv. 14)")
        if args.weights != DEFAULT_WEIGHTS:
            raise SystemExit("holdout is scored only at the locked DEFAULT_WEIGHTS (inv. 14)")
        if HOLDOUT_LOCK_PATH.exists():
            raise SystemExit(f"holdout already scored: {HOLDOUT_LOCK_PATH.name} exists (inv. 14)")

    async with connect("local") as conn:
        queries = await load_eval_set(conn)
    chosen = [q for q in queries if q.split == args.split]
    assert len(chosen) == 10, len(chosen)

    result = score_split(chosen, args.weights, random.Random(SEED))
    w = args.weights
    result["split"] = args.split
    result["weights"] = {"vector": w.vector, "file_overlap": w.file_overlap, "bm25": w.bm25}

    print(f"split {args.split}  weights v={w.vector} f={w.file_overlap} b={w.bm25}")
    for p in result["per_query"]:
        print(
            f"  #{p['query']:<5} rel {p['relevant_lenient']:>2}/{p['relevant_strict']:<2} "
            f"ceil {_fmt(p['ceiling_lenient'])}  R@3 {_fmt(p['recall_lenient'])} "
            f"strict {_fmt(p['recall_strict'])}  RR {_fmt(p['mrr_lenient'])}"
        )
    for name in METRIC_NAMES:
        s = result["metrics"][name]
        if s["mean"] is None:
            print(f"  {name:16} n/a (no scorable queries)")
            continue
        lo, hi = s["ci95"]
        print(
            f"  {name:16} {s['mean']:.3f}  95% CI [{lo:.3f}, {hi:.3f}]  "
            f"n={s['n']} excluded={s['excluded']}"
        )
    print(f"  unjudged in top-3: {result['unjudged_in_top3']} (D-P5-9 W3: must be 0)")
    print(f"  |relevant| lenient per query: {result['relevant_lenient_sizes']}")

    if args.split == "holdout":
        HOLDOUT_LOCK_PATH.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
