import pytest

from app.retrieval.signals import build_document, jaccard, tokenize


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
