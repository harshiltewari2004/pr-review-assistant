"""eval/score.py correctness. 07: tests check correctness, the harness checks
quality — nothing here asserts which PR ranks first. D-P5-17.

Holdout-guard tests replace connect() with a function that fails loudly, so
even a broken guard can never score the holdout (invariant 14).
"""

from __future__ import annotations

import asyncio
import random
import sys

import pytest

from eval import score
from eval.score import (
    bootstrap_ci,
    parse_weights,
    recall_at_k,
    recall_ceiling,
    reciprocal_rank,
    summarize,
)


def test_recall_ignores_relevant_below_k():
    # 7 is relevant but ranked 4th: only 9 counts -> 1 of 4.
    assert recall_at_k([5, 9, 2, 7], {9, 7, 1, 4}) == 0.25


def test_recall_perfect_when_all_relevant_in_top_k():
    assert recall_at_k([1, 2, 3], {1, 2, 3}) == 1.0


def test_recall_none_when_nothing_relevant():
    assert recall_at_k([5, 9, 2], set()) is None


def test_ceiling():
    assert recall_ceiling({1, 2}) == 1.0
    assert recall_ceiling({1, 2, 3, 4}) == 0.75
    assert recall_ceiling(set()) is None


def test_reciprocal_rank_first_hit():
    assert reciprocal_rank([5, 9, 2], {9, 7}) == 0.5


def test_reciprocal_rank_zero_when_hit_below_k():
    assert reciprocal_rank([5, 6, 2, 9], {9}) == 0.0


def test_reciprocal_rank_none_when_nothing_relevant():
    assert reciprocal_rank([5, 6, 2], set()) is None


def test_bootstrap_deterministic_and_brackets_mean():
    values = [0.1, 0.4, 0.4, 0.7, 0.9, 0.3, 0.5, 0.2, 0.8, 0.6]
    first = bootstrap_ci(values, random.Random(32))
    second = bootstrap_ci(values, random.Random(32))
    assert first == second
    lo, hi = first
    assert lo <= sum(values) / len(values) <= hi


def test_bootstrap_constant_values_give_zero_width():
    assert bootstrap_ci([0.5] * 10, random.Random(32)) == (0.5, 0.5)


def test_summarize_excludes_none_and_counts_it():
    s = summarize([1.0, None, 0.5], random.Random(32))
    assert s["n"] == 2
    assert s["excluded"] == 1
    assert s["mean"] == 0.75


def test_summarize_all_none():
    s = summarize([None, None], random.Random(32))
    assert s == {"mean": None, "ci95": None, "n": 0, "excluded": 2}


def test_parse_weights_valid():
    w = parse_weights("0.5,0.3,0.2")
    assert (w.vector, w.file_overlap, w.bm25) == (0.5, 0.3, 0.2)


def test_parse_weights_rejects_bad_sum():
    with pytest.raises(ValueError):
        parse_weights("0.5,0.5,0.5")


def _no_db(*args, **kwargs):
    raise AssertionError("holdout guard must refuse before touching the DB")


@pytest.fixture
def guarded(monkeypatch, tmp_path):
    monkeypatch.setattr(score, "connect", _no_db)
    monkeypatch.setattr(score, "HOLDOUT_LOCK_PATH", tmp_path / "holdout_scored.json")
    return monkeypatch


def test_holdout_refused_without_flag(guarded):
    guarded.setattr(sys, "argv", ["score", "--split", "holdout"])
    with pytest.raises(SystemExit, match="--holdout-once"):
        asyncio.run(score.main())


def test_holdout_refused_off_default_weights(guarded):
    guarded.setattr(
        sys, "argv", ["score", "--split", "holdout", "--holdout-once", "--weights", "0.4,0.4,0.2"]
    )
    with pytest.raises(SystemExit, match="DEFAULT_WEIGHTS"):
        asyncio.run(score.main())


def test_holdout_refused_when_lock_exists(guarded):
    score.HOLDOUT_LOCK_PATH.write_text("{}")
    guarded.setattr(sys, "argv", ["score", "--split", "holdout", "--holdout-once"])
    with pytest.raises(SystemExit, match="already scored"):
        asyncio.run(score.main())
