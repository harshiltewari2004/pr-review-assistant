"""Corpus filter — 04_architecture.md §5 step 2.

Applies the three metadata rules in 01_evaluation_protocol.md §2 to PR list
metadata, before diffs are fetched at step 3.

Marks, never deletes (02_data_models.md §4): a wrongly-excluded PR is one
UPDATE away from returning, and re-fetching costs a rate-limit window.

Content-based exclusion ('no_source_content') is NOT here. It runs at step 4b
in the parser path, on a diff that has already been fetched and parsed.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from ingest.constants import (
    BOT_ACCOUNTS,
    BOT_LOGIN_SUFFIX,
    DUPLICATE_WINDOW_DAYS,
    HOUSEKEEPING_TITLE_PATTERNS,
    REASON_BOT_AUTHOR,
    REASON_DUPLICATE_RESUBMISSION,
    REASON_HOUSEKEEPING,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PRMeta:
    """The list-endpoint fields the filter needs, and nothing else.

    This is a projection of GitHub's /pulls list payload, not an invented type.
    github_client.py is obligated to produce it (see from_list_item).
    """

    number: int
    title: str
    author: str
    author_type: str
    created_at: datetime
    merged_at: datetime | None


@dataclass(frozen=True)
class Verdict:
    number: int
    in_corpus: bool
    exclusion_reason: str | None


def classify(pr: PRMeta) -> str | None:
    """Per-PR metadata rules. Returns an exclusion_reason, or None to keep.

    Duplicate detection is NOT here — it is set-level and needs the whole
    list. See group_duplicates().
    """

    if pr.author_type == "Bot":
        return REASON_BOT_AUTHOR

    if pr.author.lower().removesuffix(BOT_LOGIN_SUFFIX) in BOT_ACCOUNTS:
        return REASON_BOT_AUTHOR

    for pattern in HOUSEKEEPING_TITLE_PATTERNS:
        if pattern.search(pr.title):
            return REASON_HOUSEKEEPING

    return None


_WHITESPACE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    return _WHITESPACE.sub(" ", title.strip().lower()).rstrip(".!?").strip()


def titles_match(a: str, b: str) -> bool:
    """Normalized-exact only. D-P2-4, reversed 2026-08-02.
    A SequenceMatcher ratio branch at 0.95 grouped distinct merged work as
    resubmissions - "Fix typo in p5.vector docs" and "Fix typo in p5.Color docs"
    differ by a few characters and are un related PRs.Exact matching after
    normalization is the conservative direction: a missed duplicate leaves one redundant candidate
    in the corpus, a false duplicate deletes real work from it (02 §4).
    """

    return normalize_title(a) == normalize_title(b)


def group_duplicates(prs: list[PRMeta]) -> list[list[PRMeta]]:
    """Group same-author, near-identical-title PRs inside a 7-day window.

    The window is anchored to the group's FIRST member, not the previous one,
    so a chain of near-identical titles spread over a month cannot transitively
    collapse into a single group. Groups of size 1 are not returned.
    """

    by_author: dict[str, list[PRMeta]] = {}

    for pr in prs:
        by_author.setdefault(pr.author, []).append(pr)

    window = timedelta(days=DUPLICATE_WINDOW_DAYS)
    groups: list[list[PRMeta]] = []

    for author_prs in by_author.values():
        author_prs.sort(key=lambda p: p.created_at)
        open_groups: list[list[PRMeta]] = []

        for pr in author_prs:
            for group in open_groups:
                anchor = group[0]
                if pr.created_at - anchor.created_at <= window and titles_match(
                    anchor.title, pr.title
                ):
                    group.append(pr)
                    break
            else:
                open_groups.append([pr])
        groups.extend(g for g in open_groups if len(g) > 1)

    return groups


def pick_keeper(group: list[PRMeta]) -> PRMeta:
    """01 §2: keep the merged one, else the highest PR number.

    max() over merged-only when any merged exists, so two merged siblings
    still resolve deterministically instead of raising or picking by list order.
    """

    merged = [pr for pr in group if pr.merged_at is not None]
    return max(merged or group, key=lambda p: p.number)


def apply_corpus_filter(prs: list[PRMeta]) -> list[Verdict]:
    """Step 2. Returns one Verdict per input PR, input order preserved."""
    verdicts: dict[int, Verdict] = {}
    survivors: list[PRMeta] = []

    for pr in prs:
        reason = classify(pr)
        if reason is None:
            survivors.append(pr)
        else:
            verdicts[pr.number] = Verdict(pr.number, False, reason)

    # Duplicates run on SURVIVORS only. dependabot files near-identical
    # "Bump x from 1.2 to 1.3" titles days apart; if bots reached this pass
    # they would land in the duplicate bucket and the §4 audit would report
    # the wrong reason for a large share of the corpus.
    for group in group_duplicates(survivors):
        keeper = pick_keeper(group)
        excluded = sorted(p.number for p in group if p.number != keeper.number)

        for number in excluded:
            verdicts[number] = Verdict(number, False, REASON_DUPLICATE_RESUBMISSION)
        log.info("duplicate group: kept #%d, excluded %s", keeper.number, excluded)

    for pr in prs:
        # Invariant: exclusion_reason is NULL exactly when in_corpus is TRUE.
        verdicts.setdefault(pr.number, Verdict(pr.number, True, None))

    return [verdicts[pr.number] for pr in prs]


def report_housekeeping_near_misses(prs: list[PRMeta]) -> None:
    """D-P2-5. Titles that would match the 01 §2 patterns under IGNORECASE but
    do not match as written. Read this output before the full index run.
    """

    for pr in prs:
        if any(p.search(pr.title) for p in HOUSEKEEPING_TITLE_PATTERNS):
            continue
        for p in HOUSEKEEPING_TITLE_PATTERNS:
            if re.search(p.pattern, pr.title, re.IGNORECASE):
                log.warning("housekeeping near-miss (case only): #%d %r", pr.number, pr.title)
                break
