"""Candidate set,weighted sum,ranking.03 §4, §9.

Signals are computed in signals.py; normalization in normalize.py. This
module is the only place that knows about all three at once.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime

import asyncpg
import numpy as np

from app.retrieval.constants import (
    BM25_TOP_K,
    FILE_OVERLAP_TOP_K,
    RESULTS_RETURNED,
    VECTOR_TOP_K,
    WEIGHT_BM25,
    WEIGHT_FILE_OVERLAP,
    WEIGHT_VECTOR,
)
from app.retrieval.normalize import min_max_normalize
from app.retrieval.signals import (
    Bm25Index,
    bm25_scores,
    file_overlap_signal,
    vector_backfill_for_pr,
    vector_signal_for_pr,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """The union of all three signals' nominations,plus raw scores.03 §4.

    ids is the authoritative memberships list.The three dicts are keyed by
    it and must stay keyed by it:invariant 2 requires all three signals
    normalized over the same candidate set, and three dicts with different
    key sets is exactly that invariant is failing without raising.

    Built twice per query by find_similar_prs(): first from each signal's
    uncut scores, where the key sets DIVERGE and only `ids` is used; then via
    replace() with all three dicts backfilled to exactly `ids`. Only the
    second may reach rank_candidates(); rank_candidates() raises if the
    first ever does.
    """

    ids: list[int]
    vector_raw: dict[int, float]
    file_overlap_raw: dict[int, float]
    bm25_raw: dict[int, float]


@dataclass(frozen=True, slots=True, kw_only=True)
class Weights:
    """Per-signal weights for the final score. 03 §9, invariant 5. D-P4-14.

    Validated at construction, so an invalid setting cannot reach
    rank_candidates(). The product uses DEFAULT_WEIGHTS; pool.py and
    Phase 6 tuning build their own.
    """

    vector: float
    file_overlap: float
    bm25: float

    def __post_init__(self) -> None:
        total = self.vector + self.file_overlap + self.bm25
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(f"weights must sum to 1.0 (invariant 5), got {total}")
        if min(self.vector, self.file_overlap, self.bm25) < 0.0:
            raise ValueError(f"weights must be non-negative, got {self}")


DEFAULT_WEIGHTS = Weights(
    vector=WEIGHT_VECTOR,
    file_overlap=WEIGHT_FILE_OVERLAP,
    bm25=WEIGHT_BM25,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoredCandidate:
    """One ranked candidate: final score plus per-signal norms. 03 §9, §10. D-P4-14.

    Norms are kept because reasons.py branches on them (03 §10:
    vector_norm > 0.7, bm25_norm > 0.7). Raw scores are not: no consumer.

    All four values are in [0, 1]: norms by min-max (03 §8), final_score
    because Weights is a convex combination (invariant 5).
    """

    pr_id: int
    final_score: float
    vector_score_norm: float
    file_overlap_score_norm: float
    bm25_score_norm: float


def _nominate(scores: dict[int, float], k: int) -> list[int]:
    """Top k candidates ids by score,descending.03 §4 steps 2 and 4.

    Tie-break on pr_id ascending.This is not cosmetic and it is not the
    same concern as D-P6-1's ranking ties:the cut decides MEMEBERSHIP of C,
    and C is what all three signals normalize over  (03 §8). An arbitrary
    tie-break here changes every candidates normalized score, so a rerun
    against the same snapshot could produce different published numbers
    (invariant 13).

    Measured Day 24, query #8994:25 candidates tied at exactly 0.6667 and
    48 more at 0.3333. Ties are the normal condition for file overlap on
    this corpus,not an edge case.
    """
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [pr_id for pr_id, _ in ranked[:k]]


def build_candidate_set(
    vector_raw: dict[int, float],
    file_overlap_raw: dict[int, float],
    bm25_raw: dict[int, float],
) -> CandidateSet:
    """Union the three signals' nominations into one candidate set. 03 §4 step 5.

    Each dict is that signal's UNCUT scores;the cut happens here, so the
    caller cannot accidentally cut twice or forget to.03 §4's per-signal
    caps are admission limits and belong at exactly one place.

    Union but intersection, and not vector-seeded: a PR with perfect file
    overlap but weak embedding similarity must be able to enter the ranking
    (invariant 3).Measured day 24 on #8994:file overlap alone produced a
    25-way tie for the first, so its ordering came entirely from the other two.

    ids is sorted.Set union has no defined iteration order, and the eval
    harness must rebuild the same C from teh same snapshot every run
    """

    ids = sorted(
        set(_nominate(vector_raw, VECTOR_TOP_K))
        | set(_nominate(file_overlap_raw, FILE_OVERLAP_TOP_K))
        | set(_nominate(bm25_raw, BM25_TOP_K))
    )

    return CandidateSet(
        ids=ids,
        vector_raw=vector_raw,
        file_overlap_raw=file_overlap_raw,
        bm25_raw=bm25_raw,
    )


def rank_candidates(
    candidates: CandidateSet,
    *,
    weights: Weights = DEFAULT_WEIGHTS,
    top_n: int = RESULTS_RETURNED,
) -> list[ScoredCandidate]:
    """Candidate set -> ranked ScoredCandidates. 03 §8, §9. D-P4-14.

    Pure: no I/O, no async. All three signals are normalized here, over
    candidates.ids and nowhere else, so invariant 2 holds by construction
    rather than by the caller remembering to.

    Raises if any raw dict is not keyed by exactly candidates.ids: missing
    keys AND extra keys. Extra keys mean the nominated (pre-backfill) set
    leaked in, ranking on censored vector scores (D-P4-13).

    Tie-break on pr_id ascending, matching _nominate(). Different concern:
    this one is D-P6-1's presentation order, not membership.

    Returns top_n, best first.
    """

    expected = set(candidates.ids)
    for name, raw in (
        ("vector_raw", candidates.vector_raw),
        ("file_overlap_raw", candidates.file_overlap_raw),
        ("bm25_raw", candidates.bm25_raw),
    ):
        keys = set(raw)
        if keys != expected:
            raise ValueError(
                f"{name} not keyed by candidates.ids (invariant 2): "
                f"{len(keys - expected)} extra, {len(expected - keys)} missing"
            )

    if not candidates.ids:
        return []

    vector_norm = min_max_normalize(candidates.vector_raw, candidates.ids)
    file_norm = min_max_normalize(candidates.file_overlap_raw, candidates.ids)
    bm25_norm = min_max_normalize(candidates.bm25_raw, candidates.ids)

    final = {
        pr_id: (
            weights.vector * vector_norm[pr_id]
            + weights.file_overlap * file_norm[pr_id]
            + weights.bm25 * bm25_norm[pr_id]
        )
        for pr_id in candidates.ids
    }

    ranked = sorted(final.items(), key=lambda kv: (-kv[1], kv[0]))
    return [
        ScoredCandidate(
            pr_id=pr_id,
            final_score=score,
            vector_score_norm=vector_norm[pr_id],
            file_overlap_score_norm=file_norm[pr_id],
            bm25_score_norm=bm25_norm[pr_id],
        )
        for pr_id, score in ranked[:top_n]
    ]


def _raw_range(raw: dict[int, float]) -> tuple[float, float]:
    """(min, max) of one signal's raw scores, before normalization. 04 §10."""
    return min(raw.values()), max(raw.values())


def _ms_since(started: float) -> float:
    """Milliseconds since a time.perf_counter() reading, 1 dp."""
    return round((time.perf_counter() - started) * 1000, 1)


async def build_backfilled_candidates(
    conn: asyncpg.Connection,
    index: Bm25Index,
    *,
    repo_id: int,
    query_pr_id: int,
    query_created_at: datetime,
    query_embeddings: list[np.ndarray],
    query_files: Sequence[str],
    query_tokens: list[str],
) -> CandidateSet:
    """Nominate, union, backfill. 03 §4 steps 1-6. D-P4-14.

    Returns C with all three raw dicts keyed by exactly C.ids, ready for
    rank_candidates(). Split from find_similar_prs() so eval/pool.py can
    build C once per query and rank it under several Weights: every variant
    then ranks the same C.

    Logs what only this function knows: C's size, raw ranges, and per-stage
    timings. The index is passed in, never built here: build_bm25_index()
    reads the whole corpus and belongs at startup, not per query.
    """
    timings: dict[str, float] = {}

    # 1. Raw signals, UNCUT. build_candidate_set() owns the cut (03 §4).
    # Sequential on purpose: one asyncpg connection runs one query at a time.

    started = time.perf_counter()
    vector_aggs = await vector_signal_for_pr(
        conn, query_embeddings, repo_id, query_created_at, query_pr_id
    )
    timings["vector_ms"] = _ms_since(started)

    started = time.perf_counter()
    file_raw = await file_overlap_signal(conn, query_files, repo_id, query_created_at, query_pr_id)
    timings["file_overlap_ms"] = _ms_since(started)

    started = time.perf_counter()
    bm25_raw = bm25_scores(index, query_tokens, query_created_at, query_pr_id)
    timings["bm25_ms"] = _ms_since(started)
    # 2. Nominate and union -> C. Invariant 3: union, never vector-seeded.
    nominated = build_candidate_set(
        {pr_id: agg.score_raw for pr_id, agg in vector_aggs.items()},
        file_raw,
        bm25_raw,
    )
    if not nominated.ids:
        # Earliest PRs have no past to retrieve from. Not an error.
        log.info("empty candidate set", extra={"query_pr_id": query_pr_id})
        return CandidateSet(ids=[], vector_raw={}, file_overlap_raw={}, bm25_raw={})
    # 3. Backfill all three signals over ALL of C. 03 §4 step 6, invariant 2.
    # Vector is re-scored for every member, not just the gaps: nomination
    # scores are censored (only chunks that made a top-k list), backfill
    # scores are not. Nomination decides membership; backfill decides score.
    started = time.perf_counter()
    vector_full = await vector_backfill_for_pr(
        conn,
        query_embeddings,
        repo_id,
        query_created_at,
        query_pr_id,
        candidate_ids=nominated.ids,
    )
    timings["backfill_ms"] = _ms_since(started)

    # File: absent means no shared file, so 0.0 IS the Jaccard, not a guess.
    # BM25: bm25_scores() already scored every past PR, so index directly;
    # a KeyError here would mean C holds a PR the BM25 index never saw.
    candidates = replace(
        nominated,
        vector_raw={i: vector_full[i].score_raw for i in nominated.ids},
        file_overlap_raw={i: file_raw.get(i, 0.0) for i in nominated.ids},
        bm25_raw={i: bm25_raw[i] for i in nominated.ids},
    )
    log.info(
        "candidates built",
        extra={
            "query_pr_id": query_pr_id,
            "candidate_count": len(candidates.ids),
            "vector_range": _raw_range(candidates.vector_raw),
            "file_overlap_range": _raw_range(candidates.file_overlap_raw),
            "bm25_range": _raw_range(candidates.bm25_raw),
            **timings,
        },
    )
    return candidates


async def find_similar_prs(
    conn: asyncpg.Connection,
    index: Bm25Index,
    *,
    repo_id: int,
    query_pr_id: int,
    query_created_at: datetime,
    query_embeddings: list[np.ndarray],
    query_files: Sequence[str],
    query_tokens: list[str],
    top_n: int = RESULTS_RETURNED,
) -> list[ScoredCandidate]:
    """Product path: build C, rank at DEFAULT_WEIGHTS. 03 §4, §8, §9.

    No weights parameter on purpose: tuning belongs to eval/, which calls
    build_backfilled_candidates() and rank_candidates() directly (D-P4-14).
    """
    candidates = await build_backfilled_candidates(
        conn,
        index,
        repo_id=repo_id,
        query_pr_id=query_pr_id,
        query_created_at=query_created_at,
        query_embeddings=query_embeddings,
        query_files=query_files,
        query_tokens=query_tokens,
    )

    started = time.perf_counter()
    results = rank_candidates(candidates, top_n=top_n)

    log.info(
        "query ranked",
        extra={
            "query_pr_id": query_pr_id,
            "rank_ms": _ms_since(started),
            "top": [(r.pr_id, round(r.final_score, 4)) for r in results],
        },
    )
    return results
