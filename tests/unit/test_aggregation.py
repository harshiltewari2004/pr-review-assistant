"""Chunk → PR aggregation (03 §5). Pure logic, no database."""

import pytest

from app.retrieval.signals import VectorAggregate, aggregate_chunk_scores


def test_max_takes_the_highest_observed_score():
    result = aggregate_chunk_scores({7: [0.31, 0.88, 0.52]}, strategy="max")
    assert result[7] == VectorAggregate(score_raw=0.88, chunk_hits=3)


def test_max_is_order_independent():
    """GOLDEN ASSERTION for 09 Day 18.

    MAX is associative and commutative, which is the whole reason the SQL's
    MAX over candidate chunks composes with this MAX over query chunks into
    an exact MAX over all pairs (03 §5). A loop that assigned instead of
    maxing would still produce plausible scores and raise nothing — this is
    the assertion that catches it.
    """
    scores = [0.31, 0.88, 0.52, 0.14]
    forward = aggregate_chunk_scores({7: scores}, strategy="max")
    reverse = aggregate_chunk_scores({7: list(reversed(scores))}, strategy="max")
    assert forward == reverse


def test_mean_top_k_averages_the_three_best():
    result = aggregate_chunk_scores({7: [0.9, 0.1, 0.8, 0.2, 0.7]}, strategy="mean_top_k")
    assert result[7].score_raw == pytest.approx((0.9 + 0.8 + 0.7) / 3)
    assert result[7].chunk_hits == 5


def test_mean_top_k_divides_by_observed_count_not_k():
    """A candidate seen twice divides by 2, not by MEAN_TOP_K.

    Dividing by 3 would penalize it for the VECTOR_TOP_K cutoff, which is a
    property of the query, not of the candidate. chunk_hits carries that
    evidence instead of it being baked into the score.
    """
    result = aggregate_chunk_scores({7: [0.9, 0.7]}, strategy="mean_top_k")
    assert result[7].score_raw == pytest.approx(0.8)
    assert result[7].chunk_hits == 2


def test_single_score_is_not_a_special_case():
    for strategy in ("max", "mean_top_k"):
        result = aggregate_chunk_scores({7: [0.42]}, strategy=strategy)
        assert result[7] == VectorAggregate(score_raw=0.42, chunk_hits=1)


def test_empty_score_list_raises():
    with pytest.raises(ValueError, match="no scores"):
        aggregate_chunk_scores({7: []}, strategy="max")


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="unknown aggregation strategy"):
        aggregate_chunk_scores({7: [0.5]}, strategy="mean")


def test_candidates_are_aggregated_independently():
    result = aggregate_chunk_scores({7: [0.9, 0.1], 8: [0.4]}, strategy="max")
    assert result[7].score_raw == 0.9
    assert result[8] == VectorAggregate(score_raw=0.4, chunk_hits=1)