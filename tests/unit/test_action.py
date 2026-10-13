"""The Action's comment rendering. D-P7-3, D-P4-15."""

from __future__ import annotations

from action.entry import render_comment
from app.schemas import AnalyzeResult


def result(n: int, title: str, reason: str) -> AnalyzeResult:
    return AnalyzeResult(
        pr_number=n,
        title=title,
        url=f"https://github.com/processing/p5.js/pull/{n}",
        outcome="merged",
        final_score=0.9,
        vector_score_norm=0.9,
        file_overlap_score_norm=1.0,
        bm25_score_norm=0.5,
        reason=reason,
    )


def test_one_row_per_result_with_title_link_and_reason():
    text = render_comment(
        [result(1, "A", "Also changes x.js"), result(2, "B", "Related change in src/core")],
        "processing/p5.js",
        3196,
    )
    assert (
        "| 1 | [#1 A](https://redirect.github.com/processing/p5.js/pull/1) | Also changes x.js |"
        in text
    )
    assert "| 2 | [#2 B]" in text
    assert "3,196 past processing/p5.js PRs" in text


def test_pipes_in_titles_are_escaped():
    text = render_comment([result(1, "a | b", "r")], "processing/p5.js", 1)
    assert "a \\| b" in text


def test_comment_never_links_github_com_prs_directly():
    """D-P7-4: direct github.com PR links create backlinks on upstream PRs."""
    text = render_comment([result(8120, "t", "r")], "processing/p5.js", 1)
    assert "https://github.com/processing" not in text
    assert "https://redirect.github.com/processing/p5.js/pull/8120" in text
