import pytest

from app.retrieval.signals import jaccard


def test_jaccard_identical_sets():
    assert jaccard(["a.js", "b.js"], ["b.js", "a.js"]) == 1.0


def test_jaccard_disjoint_sets():
    assert jaccard(["a.js"], ["b.js"]) == 0.0


def test_jaccard_partial_overlap():
    # 1 shared / 3 union
    assert jaccard(["a.js", "b.js"], ["b.js", "c.js"]) == pytest.approx(1 / 3)


def test_jaccard_empty_side_returns_zero_not_error():
    assert jaccard([], ["a.js"]) == 0.0
    assert jaccard(["a.js"], []) == 0.0
    assert jaccard([], []) == 0.0