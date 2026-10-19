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
from pathlib import Path

from app.retrieval.constants import VECTOR_AGGREGATION
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


def paired_bootstrap_diff(
    a: Sequence[float | None],
    b: Sequence[float | None],
    rng: random.Random,
    rounds: int = BOOTSTRAP_ROUNDS,
) -> dict:
    """Mean per-query a - b with a percentile 95% CI. D-V11-1 §6.

    Paired: each resample draws QUERIES once and both systems keep their own
    score for each drawn query, so per-query difficulty cancels. That is the
    bootstrap of the per-query differences. Queries unscorable in either
    system (None) are excluded.
    """
    diffs = [x - y for x, y in zip(a, b, strict=True) if x is not None and y is not None]
    lo, hi = bootstrap_ci(diffs, rng, rounds)
    return {
        "mean": round(sum(diffs) / len(diffs), 4),
        "ci95": [round(lo, 4), round(hi, 4)],
        "n": len(diffs),
    }


def per_rank_rates(rank_grades: Sequence[Sequence[int]], k: int = K) -> list[dict]:
    """Share of queries whose rank-r result is lenient / strict relevant, r = 1..k. D-P8-4.

    rank_grades: each query's official grades for its top k, best first (an
    unjudged result counts 0, as in score_split). The demo page shows these as
    a measured "relevant N% of the time at this rank".
    """
    n = len(rank_grades)
    rates = []
    for r in range(k):
        at_r = [g[r] for g in rank_grades if len(g) > r]
        rates.append(
            {
                "rank": r + 1,
                "lenient": round(sum(x >= LENIENT_MIN_GRADE for x in at_r) / n, 4),
                "strict": round(sum(x >= STRICT_MIN_GRADE for x in at_r) / n, 4),
            }
        )
    return rates


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


async def load_eval_set(
    conn, vector_aggregation: str = VECTOR_AGGREGATION, protocol: str = "v1.0"
) -> list[EvalQuery]:
    """All eval queries of one protocol, C built exactly as pooled, plus official labels.

    Refuses on corpus fingerprint mismatch (D-P5-9 W2): the labels judge the
    pool, the pool came from one corpus, and a changed corpus makes them stale.
    """
    proto = PROTOCOLS[protocol]
    pool = json.loads(proto.pool_path.read_text())
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
    for q in await conn.fetch(proto.queries_sql):
        judged = labels.get(q["id"], {})
        unlabeled = pooled[q["id"]] - set(judged)
        assert not unlabeled, (q["number"], f"{len(unlabeled)} pooled PRs unlabeled (W3)")
        # D-V11-7: relevance is pool-relative; labels outside this pool are not used.
        pool_labels = {cid: judged[cid] for cid in pooled[q["id"]]}
        if proto.tune_cohort is None:
            split = q["split"]
        else:
            split = "tune" if q["cohort"] == proto.tune_cohort else "holdout"
        c = await build_query_candidates(conn, index, q, vector_aggregation)
        out.append(
            EvalQuery(
                pr_id=q["id"],
                number=q["number"],
                split=split,
                candidates=c,
                labels=pool_labels,
            )
        )
    assert len(out) == proto.n_queries, len(out)
    return out


def relevant(labels: dict[int, int], min_grade: int) -> set[int]:
    """Candidates whose official grade meets the threshold (1 lenient, 2 strict)."""
    return {c for c, g in labels.items() if g >= min_grade}


def top_k(c: CandidateSet, weights: Weights, k: int = K) -> list[int]:
    """The system's top k pr_ids for one query at these weights, best first."""
    return [r.pr_id for r in rank_candidates(c, weights=weights, top_n=k)]


HOLDOUT_LOCK_PATH = POOL_PATH.parent / "holdout_scored.json"
# Pre-registered (D-P6-3): scored in the SAME single holdout run as the locked
# weights, so the comparison table (10 §2) exists without a second run.
HOLDOUT_BASELINES = {
    "vector_only": Weights(vector=1.0, file_overlap=0.0, bm25=0.0),
    "file_overlap_only": Weights(vector=0.0, file_overlap=1.0, bm25=0.0),
    "bm25_only": Weights(vector=0.0, file_overlap=0.0, bm25=1.0),
    "hybrid_prior": Weights(vector=0.5, file_overlap=0.3, bm25=0.2),
}
# D-P6-2's lock, pinned: DEFAULT_WEIGHTS moves when v1.1 locks, and this
# baseline must keep meaning "what v1.0 shipped" (D-V11-1 §6).
V10_LOCKED = Weights(vector=0.6, file_overlap=0.3, bm25=0.1)
POOL_V11_PATH = POOL_PATH.parent / "pool_v11.json"
QUERIES_V11_SQL = """
SELECT p.id, p.number, p.created_at, p.title, p.body, p.files_changed, q.split, q.cohort
FROM eval_queries q JOIN pull_requests p ON p.id = q.pr_id
ORDER BY q.cohort, q.split, p.id
"""


@dataclass(frozen=True, slots=True, kw_only=True)
class Protocol:
    """What differs between evaluation versions (D-V11-1). tune_cohort None: split from DB."""

    name: str
    pool_path: Path
    queries_sql: str
    n_queries: int
    holdout_lock_path: Path
    baselines: dict[str, Weights]
    tune_cohort: str | None


PROTOCOLS = {
    "v1.0": Protocol(
        name="v1.0",
        pool_path=POOL_PATH,
        queries_sql=QUERIES_SQL,
        n_queries=20,
        holdout_lock_path=HOLDOUT_LOCK_PATH,
        baselines=HOLDOUT_BASELINES,
        tune_cohort=None,
    ),
    # D-V11-1 §2: tune = all 20 v1.0 queries; holdout = the 20 new ones.
    "v1.1": Protocol(
        name="v1.1",
        pool_path=POOL_V11_PATH,
        queries_sql=QUERIES_V11_SQL,
        n_queries=40,
        holdout_lock_path=POOL_PATH.parent / "holdout_v11_scored.json",
        baselines=HOLDOUT_BASELINES | {"v1.0_locked": V10_LOCKED},
        tune_cohort="v1.0",
    ),
}
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
            {
                "query": q.number,
                "relevant_lenient": len(lenient),
                "relevant_strict": len(strict),
                "rank_grades": [q.labels.get(c, 0) for c in ranked],  # D-P8-4
            }
            | row
        )
    return {
        "n_queries": len(queries),
        "unjudged_in_top3": unjudged,
        "metrics": {name: summarize(values, rng) for name, values in columns.items()},
        "relevant_lenient_sizes": sorted(p["relevant_lenient"] for p in per_query),
        "per_rank": per_rank_rates([p["rank_grades"] for p in per_query]),
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
    parser.add_argument("--protocol", choices=tuple(PROTOCOLS), default="v1.0")
    parser.add_argument("--split", choices=("tune", "holdout"), default="tune")
    parser.add_argument("--weights", type=parse_weights, default=DEFAULT_WEIGHTS)
    parser.add_argument("--holdout-once", action="store_true", help="invariant 14")
    args = parser.parse_args()
    proto = PROTOCOLS[args.protocol]

    if args.split == "holdout":
        if not args.holdout_once:
            raise SystemExit("holdout needs --holdout-once: it is scored exactly once (inv. 14)")
        if args.weights != DEFAULT_WEIGHTS:
            raise SystemExit("holdout is scored only at the locked DEFAULT_WEIGHTS (inv. 14)")
        lock = proto.holdout_lock_path
        if lock.exists():
            raise SystemExit(f"holdout already scored: {lock.name} exists (inv. 14)")

    async with connect("local") as conn:
        queries = await load_eval_set(conn, protocol=proto.name)
    chosen = [q for q in queries if q.split == args.split]
    assert len(chosen) == proto.n_queries // 2, len(chosen)

    result = score_split(chosen, args.weights, random.Random(SEED))
    w = args.weights
    result["protocol"] = proto.name
    result["split"] = args.split
    result["weights"] = {"vector": w.vector, "file_overlap": w.file_overlap, "bm25": w.bm25}

    print(
        f"protocol {proto.name}  split {args.split}  "
        f"weights v={w.vector} f={w.file_overlap} b={w.bm25}"
    )
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
    for r in result["per_rank"]:
        print(f"  rank {r['rank']}: relevant {r['lenient']:.0%} lenient, {r['strict']:.0%} strict")

    # D-V11-1 §6: computed on every run, so the holdout run executes code already
    # rehearsed on tune. "Beats keyword search" only if the CI is entirely above 0.
    bm25 = score_split(chosen, HOLDOUT_BASELINES["bm25_only"], random.Random(SEED))
    diff = paired_bootstrap_diff(
        [p["recall_lenient"] for p in result["per_query"]],
        [p["recall_lenient"] for p in bm25["per_query"]],
        random.Random(SEED),
    )
    diff["beats_bm25_only"] = diff["ci95"][0] > 0
    result["lenient_minus_bm25_only"] = diff
    lo, hi = diff["ci95"]
    verdict = "beats keyword search" if diff["beats_bm25_only"] else "NOT shown to beat it"
    print(
        f"  lenient R@3 - bm25_only: {diff['mean']:+.3f}  "
        f"95% CI [{lo:+.3f}, {hi:+.3f}]  n={diff['n']}  -> {verdict}"
    )

    if args.split == "holdout":
        result["baselines"] = {}
        for name, bw in proto.baselines.items():
            b = score_split(chosen, bw, random.Random(SEED))
            result["baselines"][name] = {
                "metrics": b["metrics"],
                "unjudged_in_top3": b["unjudged_in_top3"],
            }
            m = b["metrics"]
            print(
                f"  baseline {name:<18} R@3 {_fmt(m['recall_lenient']['mean'])}  "
                f"strict {_fmt(m['recall_strict']['mean'])}  "
                f"MRR {_fmt(m['mrr_lenient']['mean'])}  unjudged {b['unjudged_in_top3']}"
            )
        proto.holdout_lock_path.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
