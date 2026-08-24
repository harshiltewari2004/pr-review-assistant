"""Per-query min-max normalization. 03 §8."""

import pytest

from app.retrieval.normalize import min_max_normalize


def test_scales_to_zero_one_over_candidate_ids():
    """Invariant 5's precondition:normalized values land in [0,1]

    The weighted sum can only guarantee final_score in [0,1] if every
    signal it sums is already in [0,1]. This is where it holds.
    """

    raw = {1: 2.0, 2: 4.0, 3: 6.0}

    out = min_max_normalize(raw, [1, 2, 3])

    assert out == {1: 0.0, 2: 0.5, 3: 1.0}


def test_degenerate_case_returns_zero_not_nan():
    """Invariant 4.Never NaN,never a divison error.

    Measured Day 24 on query #8994:25 candidates tied at exactly 0.6667.
    A candidate set drawn only from a tie cluster is not hypothetical on
    this corpus - it is what life overlap produces when the cap binds
    inside one.
    """

    raw = {1: 0.6667, 2: 0.6667, 3: 0.6667}

    out = min_max_normalize(raw, [1, 2, 3])

    assert out == {1: 0.0, 2: 0.0, 3: 0.0}


def test_extra_test_keys_in_raw_are_ignored():
    """raw may hold MORE than C and must not be scaled by the surplus.

    file_overlap_signal() returns uncapped:148 candidates on #8994 when
    only 100 were nominated. If lo/hi came from all 148, the normalization
    would be scaled by candidates absent from the ranking entirely.
    """

    raw = {1: 0.0, 2: 5.0, 3: 10.0, 99: 1000.0}

    out = min_max_normalize(raw, [1, 2, 3])

    assert out == {1: 0.0, 2: 0.5, 3: 1.0}
    assert 99 not in out


def test_missing_candidate_raises():
    """Invariant 2, enforced. The backfill hole must not pass silently.

    A candidate in C with no score for this signal is 03 §4 step 6 not
    having fun. Filling 0.0 would become the min-max floor and rescale
    every other candidate.
    """
    raw = {1: 0.5, 2: 0.9}

    with pytest.raises(ValueError, match="backfill"):
        min_max_normalize(raw, [1, 2, 3])


def test_empty_candidate_ids_raises():
    """An empty C means all three signals nominated nothing - impossible
    for a PR with chunks,files and a title, so it is called a bug."""
    with pytest.raises(ValueError, match="empty"):
        min_max_normalize({1: 0.5}, [])
