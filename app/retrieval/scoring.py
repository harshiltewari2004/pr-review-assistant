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
    second may reach rank_candidates(); min_max_normalize() raises if the
    first ever does.
    """

    ids: list[int]
    vector_raw: dict[int, float]
    file_overlap_raw: dict[int, float]
    bm25_raw: dict[int, float]


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
    top_n: int = RESULTS_RETURNED,
) -> list[tuple[int, float]]:
    """Candidate set -> rank(pr_id,final_score). 03 §8, §9.

    Pure:no I/O, no async.All three signals are normalized here,over
    candidates.id over nowhere else, so invariant 2 holds by construction
    rather than by the caller remembering to.

    Tie-break on pr_id ascending,matching_nominate().Different concern
    though:this one. is DP-6-1's presentation order,not membership.

    Returns top_n,best first.
    """

    total = WEIGHT_VECTOR + WEIGHT_FILE_OVERLAP + WEIGHT_BM25
    if not math.isclose(total, 1.0, abs_tol=1e-9):
        raise ValueError(f"weights must sum to 1.0 (invariant 5),got{total}")

    vector_norm = min_max_normalize(candidates.vector_raw, candidates.ids)
    file_norm = min_max_normalize(candidates.file_overlap_raw, candidates.ids)
    bm25_norm = min_max_normalize(candidates.bm25_raw, candidates.ids)

    final = {
        pr_id: (
            WEIGHT_VECTOR * vector_norm[pr_id]
            + WEIGHT_FILE_OVERLAP * file_norm[pr_id]
            + WEIGHT_BM25 * bm25_norm[pr_id]
        )
        for pr_id in candidates.ids
    }

    ranked = sorted(final.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:top_n]


def _raw_range(raw: dict[int, float]) -> tuple[float, float]:
    """(min, max) of one signal's raw scores, before normalization. 04 §10."""
    return min(raw.values()), max(raw.values())


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
) -> list[tuple[int, float]]:
    """Nominate ,union,backfill,rank.03 §4 steps 1-6, §8, §9.

    The index is passed in,never built here:build_bm25_index() reads the
    whole corpus and belongs at startup , not per query.
    """

    # 1. Raw signals, UNCUT. build_candidate_set() owns the cut (03 §4).
    # Sequential on purpose: one asyncpg connection runs one query at a time.

    vector_aggs = await vector_signal_for_pr(
        conn, query_embeddings, repo_id, query_created_at, query_pr_id
    )
    file_raw = await file_overlap_signal(conn, query_files, repo_id, query_created_at, query_pr_id)
    bm25_raw = bm25_scores(index, query_tokens, query_created_at, query_pr_id)
    # 2. Nominate and union -> C. Invariant 3: union, never vector-seeded.
    nominated = build_candidate_set(
        {pr_id: agg.score_raw for pr_id, agg in vector_aggs.items()},
        file_raw,
        bm25_raw,
    )
    if not nominated.ids:
        # Earliest PRs have no past to retrieve from. Not an error.
        log.info("empty candidate set", extra={"query_pr_id": query_pr_id})
        return []
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
    backfill_ms = (time.perf_counter() - started) * 1000

    # File: absent means no shared file, so 0.0 IS the Jaccard, not a guess.
    # BM25: bm25_scores() already scored every past PR, so index directly;
    # a KeyError here would mean C holds a PR the BM25 index never saw.
    candidates = replace(
        nominated,
        vector_raw={i: vector_full[i].score_raw for i in nominated.ids},
        file_overlap_raw={i: file_raw.get(i, 0.0) for i in nominated.ids},
        bm25_raw={i: bm25_raw[i] for i in nominated.ids},
    )
    # 4. Normalize over C, weight, rank. 03 §8, §9. Invariant 2 holds because
    # every dict in `candidates` is keyed by exactly C.
    results = rank_candidates(candidates, top_n)

    log.info(
        "query scored",
        extra={
            "query_pr_id": query_pr_id,
            "candidate_count": len(candidates.ids),
            "vector_range": _raw_range(candidates.vector_raw),
            "file_overlap_range": _raw_range(candidates.file_overlap_raw),
            "bm25_range": _raw_range(candidates.bm25_raw),
            "backfill_ms": round(backfill_ms, 1),
            "top": results,
        },
    )
    return results
