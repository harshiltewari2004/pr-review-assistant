"""Candidate set constructions.03 §4."""

import pytest

from app.retrieval.scoring import (
    CandidateSet,
    ScoredCandidate,
    Weights,
    build_candidate_set,
    rank_candidates,
)


def test_union_introduces_no_candidate_absent_from_every_signal():
    """Invarinat 1, structural half. 07 §4.

    Each signal enforces the temporal filter at its own source:p.created_at
    <$3 in VECTOR_SIGNAL_SQL and FILE_CANDIDATES_SQL, and in Python inside
    bm25_signal().Set union cannot produce a number that was in no input,
    so a temporarlly-clean input gurantess a temporally-clean C.

    This is the assertion that makes the whole filter chain sound :it is why
    the filter does NOT need re-enforcing here, and why re-enforcing it here
    would hide a leak in a signal rather than surface it.
    """

    vector = {1: 0.9, 2: 0.8}
    files = {2: 0.5, 3: 0.4}
    bm25 = {3: 7.0, 4: 6.5}

    c = build_candidate_set(vector, files, bm25)

    assert set(c.ids) <= set(vector) | set(files) | set(bm25)
    assert c.ids == [1, 2, 3, 4]


# --- D-P4-14: Weights ---------------------------------------------------


def test_weights_reject_bad_sum():
    with pytest.raises(ValueError, match="sum to 1"):
        Weights(vector=0.5, file_overlap=0.3, bm25=0.3)


def test_weights_accept_float_rounding_sum():
    # 0.7 + 0.2 + 0.1 == 0.9999999999999999; an == 1.0 guard would reject it.
    Weights(vector=0.7, file_overlap=0.2, bm25=0.1)


def test_weights_reject_negative_component():
    # Sums to 1.0 but final_score could reach -0.5 (invariant 5 needs convexity).
    with pytest.raises(ValueError, match="non-negative"):
        Weights(vector=1.5, file_overlap=-0.5, bm25=0.0)


def test_weights_are_keyword_only():
    with pytest.raises(TypeError):
        Weights(0.5, 0.3, 0.2)


# --- D-P4-14: rank_candidates -------------------------------------------

_IDS = [1, 2, 3, 4]
_VECTOR = {1: 0.9, 2: 0.5, 3: 0.7, 4: 0.2}
_FILE = {1: 0.0, 2: 0.67, 3: 0.33, 4: 0.0}
_BM25 = {1: 52.0, 2: 298.0, 3: 120.0, 4: 80.0}


def _candidates(vector=_VECTOR, file_overlap=_FILE, bm25=_BM25, ids=_IDS):
    return CandidateSet(
        ids=list(ids),
        vector_raw=dict(vector),
        file_overlap_raw=dict(file_overlap),
        bm25_raw=dict(bm25),
    )


def test_rank_candidates_rejects_extra_key():
    # The Day 28 hole: nominated set's uncut dicts cover C plus extras.
    with pytest.raises(ValueError, match="vector_raw not keyed.*1 extra"):
        rank_candidates(_candidates(vector={**_VECTOR, 5: 0.99}))


def test_rank_candidates_rejects_missing_key():
    vector = {k: v for k, v in _VECTOR.items() if k != 4}
    with pytest.raises(ValueError, match="vector_raw not keyed.*1 missing"):
        rank_candidates(_candidates(vector=vector))


def test_rank_candidates_empty_set_returns_empty():
    assert rank_candidates(_candidates(vector={}, file_overlap={}, bm25={}, ids=[])) == []


def test_rank_candidates_scores_bounded():
    # 07 §5 scoring invariant: final_score and every norm in [0, 1].
    results = rank_candidates(_candidates(), top_n=len(_IDS))
    assert len(results) == len(_IDS)
    for r in results:
        assert isinstance(r, ScoredCandidate)
        for v in (r.final_score, r.vector_score_norm, r.file_overlap_score_norm, r.bm25_score_norm):
            assert 0.0 <= v <= 1.0


def test_vector_only_weights_preserve_raw_vector_order():
    # D-P4-14: min-max is monotonic, so Weights(1, 0, 0) is exactly vector-only.
    results = rank_candidates(
        _candidates(),
        weights=Weights(vector=1.0, file_overlap=0.0, bm25=0.0),
        top_n=len(_IDS),
    )
    expected = sorted(_IDS, key=lambda i: (-_VECTOR[i], i))
    assert [r.pr_id for r in results] == expected
