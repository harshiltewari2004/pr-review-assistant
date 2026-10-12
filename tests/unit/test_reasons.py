"""reasons.py correctness: the 03 §10 rule chain, thresholds, and product
language (invariants 17, 18). Pure functions only; no DB. D-P4-11, D-P4-15.
"""

from __future__ import annotations

import pytest

from app.retrieval.reasons import (
    build_reason,
    closest_file,
    shared_file,
    top_directory,
    top_matched_terms,
)

Q = ["src/webgl/p5.RendererGL.js"]


def reason(vector=0.1, bm25=0.1, cand=("src/core/main.js",), terms=(), outcome="merged"):
    return build_reason(
        vector_norm=vector,
        bm25_norm=bm25,
        query_files=Q,
        candidate_files=list(cand),
        matched_terms=list(terms),
        outcome=outcome,
    )


def test_rule1_shared_file_and_high_vector():
    assert reason(vector=0.9, cand=Q) == f"Both modify {Q[0]} with a similar change pattern"


def test_rule2_threshold_is_strict():
    assert reason(vector=0.7, cand=Q) == f"Also changes {Q[0]}"


def test_rule3_high_vector_no_shared_file():
    got = reason(vector=0.9, cand=["src/webgl/p5.Shader.js"])
    assert got == "Similar change pattern in src/webgl/p5.Shader.js"


def test_rule4_high_bm25_with_terms():
    got = reason(bm25=0.8, terms=["framebuffer", "density"])
    assert got == "Shares terminology: framebuffer, density"


def test_rule4_without_terms_falls_to_rule5():
    assert reason(bm25=0.8, terms=[]).startswith("Related change in")


def test_rule5_fallback_names_the_directory():
    assert reason() == "Related change in src/core"


def test_closed_unmerged_suffix_and_never_rejected():
    assert reason(outcome="closed_unmerged").endswith(
        " — closed without merging, worth checking why"
    )
    for outcome in ("merged", "closed_unmerged", "open"):
        assert "rejected" not in reason(outcome=outcome).lower()


def test_unknown_outcome_raises():
    with pytest.raises(AssertionError):
        reason(outcome="rejected")


def test_shared_file_is_deterministic():
    assert shared_file(["b.js", "a.js"], ["a.js", "b.js"]) == "a.js"
    assert shared_file(["a.js"], ["c.js"]) is None


def test_closest_file_ties_go_alphabetical():
    assert closest_file(["src/x/q.js"], ["src/y/b.js", "src/y/a.js"]) == "src/y/a.js"


def test_top_matched_terms_rarest_first_ties_alphabetical():
    idf = {"render": 0.1, "b": 2.0, "a": 2.0, "zz": 5.0}
    assert top_matched_terms(["render", "a", "b", "zz"], ["zz", "b", "a", "render"], idf) == [
        "zz",
        "a",
    ]


def test_top_directory_root():
    assert top_directory("README.md") == "the repository root"
