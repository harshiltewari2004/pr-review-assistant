"""Candidate set,weighted sum,ranking.03 §4, §9.

Signals are computed in signals.py; normalization in normalize.py. This
module is the only place that knows about all three at once.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.retrieval.constants import BM25_TOP_K, FILE_OVERLAP_TOP_K, VECTOR_TOP_K


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """The union of all three signals' nominations,plus raw scores.03 §4.

    ids is the authoritative memberships list.The three dicts are keyed by
    it and must stay keyed by it:invariant 2 requires all three signals
    normalized over the same candidate set, and three dicts with different
    key sets is exactly that invariant is failing without raising.

    NOMINATION-ONLY as of Day-24.Each dict currently holds scores only
    for the candidates its own signal surfaced ,so the key sets DIVERGE and
    invariant 2 is not met yet.03 §4 step 6(backfill) closes this and must
     land before day 25 pooling.
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
