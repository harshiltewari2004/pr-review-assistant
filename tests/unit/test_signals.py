from datetime import UTC, datetime

import pytest
from rank_bm25 import BM25Okapi

from app.retrieval.signals import Bm25Index, bm25_signal, build_document, jaccard, tokenize


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


def test_tokenize_snake_case_keeps_whole_and_parts():
    # 07 §4: the whole identifier AND its sub-tokens.
    assert tokenize("jsonable_encoder") == ["jsonable_encoder", "jsonable", "encoder"]


def test_tokenize_camel_case_splits_on_boundaries():
    assert tokenize("formatSseEvent") == ["formatsseevent", "format", "sse", "event"]


def test_tokenize_plain_word_emits_once():
    # len(parts) > 1 guard: emitting both would double the term frequency.
    assert tokenize("encoder") == ["encoder"]


def test_tokenize_preserves_repeats_for_term_frequency():
    assert tokenize("vector vector") == ["vector", "vector"]


def test_build_document_uses_basenames_not_paths():
    doc = build_document("fix", None, ["src/webgl/p5.Shader.js"])
    assert "src" not in doc
    assert "webgl" not in doc
    assert "shader" in doc


def test_build_document_handles_none_body():
    assert build_document("fix vector", None, []) == ["fix", "vector"]


def _dt(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=UTC)


# BM25 IDF is log(N - df + 0.5) - log(df + 0.5). In a 2-document corpus
# where the query term appears in both, that is NEGATIVE — and rank-bm25's
# negative-IDF correction (epsilon * average_idf) is also negative when
# every IDF is negative. Padding makes df small relative to N, which is
# the regime BM25 is defined for. Padding docs share no terms with any
# query, so they score 0.0 and the guard drops them.
_PADDING = [(10_000 + i, 1, f"unrelated padding term{i}") for i in range(20)]


def _index(docs: list[tuple[int, int, str]]) -> Bm25Index:
    """(pr_id, day, text) -> a Bm25Index over those documents, plus padding."""
    all_docs = docs + _PADDING
    return Bm25Index(
        bm25=BM25Okapi([tokenize(text) for _, _, text in all_docs]),
        pr_ids=[pr_id for pr_id, _, _ in all_docs],
        created_ats=[_dt(day) for _, day, _ in all_docs],
    )


def test_bm25_signal_excludes_future_candidates():
    # Invariant 1. No SQL to enforce it — this is the only guard.
    idx = _index([(1, 1, "vector maths"), (2, 9, "vector maths")])
    out = bm25_signal(idx, tokenize("vector"), _dt(5), query_pr_id=99)
    assert [pr for pr, _ in out] == [1]


def test_bm25_signal_excludes_the_query_pr_itself():
    idx = _index([(1, 1, "vector maths"), (2, 2, "vector maths")])
    out = bm25_signal(idx, tokenize("vector"), _dt(5), query_pr_id=1)
    assert [pr for pr, _ in out] == [2]


def test_bm25_signal_drops_zero_score_documents():
    # Score 0.0 means no shared terms — provably a non-candidate,
    # unlike VECTOR_TOP_K's "below the cutoff".
    idx = _index([(1, 1, "vector maths"), (2, 1, "shader webgl")])
    out = bm25_signal(idx, tokenize("vector"), _dt(5), query_pr_id=99)
    assert [pr for pr, _ in out] == [1]


def test_bm25_signal_filters_before_the_cut():
    # PRs 5 and 6 are SHORT, so length normalization scores them highest —
    # and both are ineligible. Cutting to top_k before filtering would
    # return one result instead of three. 03 §4 step 3.
    long = "vector " + " ".join(f"filler{i}" for i in range(40))
    idx = _index(
        [
            (1, 1, long),
            (2, 2, long),
            (3, 3, long),
            (4, 4, long),
            (5, 8, "vector"),
            (6, 9, "vector"),
        ]
    )
    out = bm25_signal(idx, tokenize("vector"), _dt(5), query_pr_id=99, top_k=3)
    assert len(out) == 3
    assert all(pr in (1, 2, 3, 4) for pr, _ in out)


def test_bm25_signal_breaks_ties_by_pr_id():
    # Identical documents score identically. D-P6-1: deterministic order.
    idx = _index([(7, 1, "vector"), (3, 1, "vector"), (5, 1, "vector")])
    out = bm25_signal(idx, tokenize("vector"), _dt(5), query_pr_id=99)
    assert [pr for pr, _ in out] == [3, 5, 7]


def test_bm25_signal_requires_timezone_aware_datetime():
    idx = _index([(1, 1, "vector")])
    with pytest.raises(ValueError):
        bm25_signal(idx, tokenize("vector"), datetime(2026, 1, 5), query_pr_id=99)
