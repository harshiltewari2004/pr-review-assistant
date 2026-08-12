"""List item + parsed diff -> a pull_requests row (02 §4).

Pure: no DB, no network, no file reads. The caller supplies the diff text.
files_changed, additions and deletions all derive from parse_hunks output
(D-P2-14) and will NOT match GitHub's own PR-page totals.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from app.retrieval.chunking import diff_totals, files_changed, parse_hunks
from ingest.constants import REASON_NO_SOURCE_CONTENT


class PRRow(NamedTuple):
    number: int
    github_id: int
    title: str
    body: str | None
    author: str
    author_type: str
    outcome: str
    labels: list[str]
    files_changed: list[str]
    additions: int
    deletions: int
    created_at: str
    merged_at: str | None
    closed_at: str | None
    in_corpus: bool
    exclusion_reason: str | None
    raw: dict[str, Any]


def outcome_of(item: dict[str, Any]) -> str:
    """02 §4: three values. Never 'rejected' — GitHub has no such state."""
    if item.get("merged_at"):
        return "merged"
    return "closed_unmerged" if item["state"] == "closed" else "open"


def build_row(
    item: dict[str, Any],
    *,
    in_corpus: bool,
    exclusion_reason: str | None,
    diff: str | None,
) -> PRRow:
    """diff is None when none was fetched: step-2 exclusions and the 19 406s.

    Reason precedence, highest first:
      1. step 2's verdict      — no diff exists to parse
      2. diff_unavailable      — 406 at step 3 (D-P2-2)
      3. no_source_content     — parsed to zero hunks (04 §5 step 4b)
    The `diff is not None` guard is what keeps 2 from being overwritten by 3.
    """
    hunks = parse_hunks(diff) if diff is not None else []
    additions, deletions = diff_totals(hunks)

    if in_corpus and diff is not None and not hunks:
        in_corpus = False
        exclusion_reason = REASON_NO_SOURCE_CONTENT

    return PRRow(
        number=item["number"],
        github_id=item["id"],
        title=item["title"],
        body=item.get("body"),
        author=item["user"]["login"],
        author_type=item["user"]["type"],
        outcome=outcome_of(item),
        labels=[label["name"] for label in item["labels"]],
        files_changed=files_changed(hunks),
        additions=additions,
        deletions=deletions,
        created_at=item["created_at"],
        merged_at=item.get("merged_at"),
        closed_at=item.get("closed_at"),
        in_corpus=in_corpus,
        exclusion_reason=exclusion_reason,
        raw=item,
    )
