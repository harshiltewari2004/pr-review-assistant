"""v1.1 scorer additions, pure: paired bootstrap (D-V11-1 §6), per-rank rates (D-P8-4)."""

import random

from eval.score import paired_bootstrap_diff, per_rank_rates


def test_paired_bootstrap_cancels_query_difficulty():
    # Per-query scores range 0.0-0.9, but a beats b by exactly 0.1 on every
    # query. Pairing keeps each query's two scores together, so the CI
    # collapses to 0.1; unpaired CIs would be wide and overlap.
    a = [0.1, 0.9, 0.2, 0.8, 0.5]
    b = [0.0, 0.8, 0.1, 0.7, 0.4]
    assert paired_bootstrap_diff(a, b, random.Random(32)) == {
        "mean": 0.1,
        "ci95": [0.1, 0.1],
        "n": 5,
    }


def test_paired_bootstrap_skips_queries_unscorable_in_either():
    d = paired_bootstrap_diff([0.5, None, 0.3], [0.5, 0.2, None], random.Random(32))
    assert d["n"] == 1
    assert d["mean"] == 0.0


def test_paired_bootstrap_is_deterministic():
    a, b = [0.3, 0.6, 0.1, 0.9], [0.4, 0.2, 0.1, 0.5]
    first = paired_bootstrap_diff(a, b, random.Random(32))
    assert first == paired_bootstrap_diff(a, b, random.Random(32))


def test_per_rank_rates():
    grades = [[2, 0, 1], [1, 1, 0], [0, 0, 0], [2, 2, 2]]
    assert per_rank_rates(grades) == [
        {"rank": 1, "lenient": 0.75, "strict": 0.5},
        {"rank": 2, "lenient": 0.5, "strict": 0.25},
        {"rank": 3, "lenient": 0.5, "strict": 0.25},
    ]
