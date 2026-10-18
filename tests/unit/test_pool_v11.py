"""v1.1 pool, pure core. D-V11-1 §3, D-V11-4, D-P5-9 W3.

Synthetic candidate sets only: no DB. Checks pooling rules, never which PR
is relevant (07: tests check correctness, the harness checks quality).
"""

from app.retrieval.scoring import CandidateSet, Weights
from eval.pool import pool_for_query
from eval.pool_v11 import V10_LOCKED, pool_v11_for_query, scored_configs
from eval.score import HOLDOUT_BASELINES, top_k

_IDS = list(range(1, 11))


def _c():
    # PR 1 is weakest on every signal; only 9 and 10 share files.
    return CandidateSet(
        ids=list(_IDS),
        vector_raw={i: 0.1 * i for i in _IDS},
        file_overlap_raw={i: 0.0 for i in _IDS} | {9: 0.5, 10: 0.25},
        bm25_raw={i: 10.0 * i for i in _IDS},
    )


def test_scorer_zero_evidence_pick_is_pooled():
    # The scorer's file-only top 3 fills slot 3 by tie-break with PR 1 (zero
    # evidence), which every D-P5-8 variant leaves out. It must be pooled, or
    # that config's top 3 holds an unjudged PR (W3).
    c = _c()
    file_only = Weights(vector=0.0, file_overlap=1.0, bm25=0.0)
    assert top_k(c, file_only) == [9, 10, 1]
    assert 1 not in pool_for_query(c)
    pool = pool_v11_for_query(c, [file_only])
    assert 1 in pool
    assert pool == sorted(pool)


def test_scored_configs_dedupe_to_grid_and_cover_baselines():
    configs = scored_configs()
    keys = {(w.vector, w.file_overlap, w.bm25) for w in configs}
    assert len(configs) == len(keys) == 66
    for w in (*HOLDOUT_BASELINES.values(), V10_LOCKED):
        assert (w.vector, w.file_overlap, w.bm25) in keys
