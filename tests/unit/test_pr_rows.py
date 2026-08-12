"""build_row branch coverage — 04 §5 steps 2, 3, 4b.

Case 3 is the point of this file: diff_unavailable must survive the
zero-hunk branch. Both produce an empty file list, so a precedence bug
is invisible in the row's shape and visible only in the reason.
"""

from __future__ import annotations

from pathlib import Path

from ingest.constants import (
    REASON_DIFF_UNAVAILABLE,
    REASON_HOUSEKEEPING,
    REASON_NO_SOURCE_CONTENT,
)
from ingest.pr_rows import build_row

FIXTURES = Path(__file__).parent.parent / "fixtures" / "diffs"


def load(name: str) -> str:
    return (FIXTURES / f"{name}.diff").read_text()


def item(number: int = 1234, **overrides) -> dict:
    """Only the keys build_row touches."""
    base = {
        "number": number,
        "id": 900_000 + number,
        "title": "Fix pixel density on retina",
        "body": "closes #1",
        "user": {"login": "someone", "type": "User"},
        "state": "closed",
        "merged_at": "2024-03-02T10:00:00Z",
        "closed_at": "2024-03-02T10:00:00Z",
        "created_at": "2024-03-01T09:00:00Z",
        "labels": [{"name": "Bug"}],
    }
    base.update(overrides)
    return base


def test_in_corpus_pr_with_source_diff():
    row = build_row(
        item(),
        in_corpus=True,
        exclusion_reason=None,
        diff=load("generated_excluded"),
    )
    assert row.in_corpus is True
    assert row.exclusion_reason is None
    assert row.files_changed == ["src/core/main.js"]
    assert row.additions == 1
    assert row.outcome == "merged"


def test_step2_exclusion_keeps_its_reason_and_parses_nothing():
    row = build_row(
        item(),
        in_corpus=False,
        exclusion_reason=REASON_HOUSEKEEPING,
        diff=None,
    )
    assert row.in_corpus is False
    assert row.exclusion_reason == REASON_HOUSEKEEPING
    assert row.files_changed == []
    assert (row.additions, row.deletions) == (0, 0)


def test_diff_unavailable_is_not_overwritten_by_zero_hunk():
    row = build_row(
        item(),
        in_corpus=False,
        exclusion_reason=REASON_DIFF_UNAVAILABLE,
        diff=None,
    )
    assert row.exclusion_reason == REASON_DIFF_UNAVAILABLE


def test_zero_hunk_diff_becomes_no_source_content():
    row = build_row(
        item(),
        in_corpus=True,
        exclusion_reason=None,
        diff=load("md_only"),
    )
    assert row.in_corpus is False
    assert row.exclusion_reason == REASON_NO_SOURCE_CONTENT
    assert row.files_changed == []


def test_open_pr_outcome():
    row = build_row(
        item(state="open", merged_at=None, closed_at=None),
        in_corpus=True,
        exclusion_reason=None,
        diff=load("generated_excluded"),
    )
    assert row.outcome == "open"
