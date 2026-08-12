"""List item + parsed diff -> a pull_requests row (02 §4).

Pure: no DB, no network, no file reads. The caller supplies the diff text.
files_changed, additions and deletions all derive from parse_hunks output
(D-P2-14) and will NOT match GitHub's own PR-page totals.
"""

from __future__ import annotations

from datetime import datetime
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
    created_at: datetime
    merged_at: datetime | None
    closed_at: datetime | None
    in_corpus: bool
    exclusion_reason: str | None
    raw: dict[str, Any]


def outcome_of(item: dict[str, Any]) -> str:
    """02 §4: three values. Never 'rejected' — GitHub has no such state."""
    if item.get("merged_at"):
        return "merged"
    return "closed_unmerged" if item["state"] == "closed" else "open"


def _ts(value: str | None) -> datetime | None:
    """GitHub returns '2024-03-01T09:00:00Z'. Python 3.11's fromisoformat
    handles the Z suffix natively; 3.10 and earlier do not.
    """
    return datetime.fromisoformat(value) if value else None


_RAW_DROP = ("base", "head", "links")


def _lean_raw(item: dict[str, Any]) -> dict[str, Any]:
    """02 §4 keeps raw for future use but never filters on it. base/head/_links
    are 80% of the payload (58.7 MB of 73.5 across 4,372 PRs, measured
    2026-08-12) and base.repo duplicates the repos table row-for-row. head.sha
    is kept: it is the only identifier of the commit state a diff was fetched
    at, which the frozen-snapshot claim in 01 §15 depends on. D-P2-27.
    """
    lean = {k: v for k, v in item.items() if k not in _RAW_DROP}
    head = item.get("head") or {}
    lean["head_sha"] = head.get("sha")
    return lean


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
        created_at=_ts(item["created_at"]),
        merged_at=_ts(item.get("merged_at")),
        closed_at=_ts(item.get("closed_at")),
        in_corpus=in_corpus,
        exclusion_reason=exclusion_reason,
        raw=_lean_raw(item),
    )
