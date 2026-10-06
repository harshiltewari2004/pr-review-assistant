"""Pool construction, pure core. 01 §9, D-P5-8, D-P5-9 W1.

Synthetic candidate sets only: no DB. These check pooling rules, never which
PR is relevant (07: tests check correctness, the harness checks quality).
"""

import pytest

from app.retrieval.scoring import DEFAULT_WEIGHTS, CandidateSet
from eval.pool import POOL_DEPTH, VARIANTS, Variant, pool_for_query, variant_picks

_IDS = [1, 2, 3, 4, 5, 6, 7, 8]
_VECTOR = {1: 0.9, 2: 0.8, 3: 0.7, 4: 0.6, 5: 0.5, 6: 0.4, 7: 0.3, 8: 0.2}
_BM25 = {i: 10.0 * i for i in _IDS}


def _c(file_overlap, ids=_IDS, vector=_VECTOR, bm25=_BM25):
    return CandidateSet(
        ids=list(ids),
        vector_raw={i: vector[i] for i in ids},
        file_overlap_raw={i: file_overlap[i] for i in ids},
        bm25_raw={i: bm25[i] for i in ids},
    )


def test_single_signal_variant_skips_zero_evidence():
    # Only 1 and 2 share files; the other 6 must not pad the file-only picks.
    file_overlap = {i: 0.0 for i in _IDS} | {1: 0.5, 2: 0.25}
    assert variant_picks(_c(file_overlap))["file_overlap"] == [1, 2]


def test_all_zero_evidence_contributes_nothing():
    # The #7978 case: no candidate shares a file with the query.
    picks = variant_picks(_c({i: 0.0 for i in _IDS}))
    assert picks["file_overlap"] == []


def test_evidence_uses_raw_not_norm():
    # All three share files; PR 3 has the lowest raw, so its norm is 0.0.
    # Raw 0.2 is real evidence: it must still be pooled.
    ids = [1, 2, 3]
    picks = variant_picks(_c({1: 0.6, 2: 0.4, 3: 0.2}, ids=ids))
    assert picks["file_overlap"] == [1, 2, 3]


def test_hybrid_variants_are_not_evidence_filtered():
    picks = variant_picks(_c({i: 0.0 for i in _IDS}))
    assert len(picks["hybrid_default"]) == POOL_DEPTH
    assert len(picks["hybrid_equal"]) == POOL_DEPTH


def test_pool_is_sorted_union_bounded_by_depth():
    c = _c({i: 0.1 * i for i in _IDS})
    pool = pool_for_query(c)
    union = set().union(*variant_picks(c).values())
    assert pool == sorted(union)
    assert len(pool) <= len(VARIANTS) * POOL_DEPTH


def test_empty_candidate_set_gives_empty_pool():
    c = CandidateSet(ids=[], vector_raw={}, file_overlap_raw={}, bm25_raw={})
    assert all(ids == [] for ids in variant_picks(c).values())
    assert pool_for_query(c) == []


def test_variant_rejects_unknown_evidence_field():
    with pytest.raises(ValueError, match="unknown evidence field"):
        Variant(name="typo", weights=DEFAULT_WEIGHTS, evidence="bm25raw")
