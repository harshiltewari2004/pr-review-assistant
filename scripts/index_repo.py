"""Local indexing pipeline (04 §5). Run: python -m scripts.index_repo processing/p5.js

Steps 1-7 land here incrementally; step 1 (fetch PR list) is implemented.
Raw pages are cached inside GitHubClient before parsing (invariant 19).
Imports ingest/ — never app/, never eval/ (04 §3).
"""

from __future__ import annotations

import logging
import os
import sys
import time
from collections import Counter
from typing import Any, NamedTuple

from ingest.constants import (
    EXPECTED_FIRST_NUMBER,
    EXPECTED_TOTAL_HIGH,
    EXPECTED_TOTAL_LOW,
    PER_PAGE,
    STEP2_EXCLUSION_REASONS,
)
from ingest.github_client import GitHubClient

log = logging.getLogger(__name__)

# Pre-registered before the first run (01 §14). Written down, then tested.


class ListFetch(NamedTuple):
    items: list[dict[str, Any]]
    pages: int
    last_page_size: int


def fetch_all(gh: GitHubClient) -> ListFetch:
    """Every /pulls page for the repo, raw items preserved.

    A missing page is run-level, not PR-level: 04 §5's never-hard-fail rule
    covers per-PR diff errors at step 3, where one loss costs one candidate.
    A dropped list page is a silent hole in the corpus, so the RuntimeError
    from _request is left to propagate.
    """
    items: list[dict[str, Any]] = []
    pages = last = 0
    for page, raw in gh.iter_list_pages():
        pages, last = page, len(raw)
        items.extend(raw)
        log.info("page %4d: %3d items — %5d total", page, last, len(items))
    return ListFetch(items, pages, last)


def assert_list_is_sound(fetch: ListFetch) -> None:
    """Golden assertion for step 1, written before the run (07 §3)."""
    items, page, last = fetch
    assert items, "no items fetched"

    numbers = [i["number"] for i in items]

    dupes = sorted(n for n, c in Counter(numbers).items() if c > 1)
    assert not dupes, f"duplicate PR numbers across pages:{dupes[:10]}"

    breaks = [(a, b) for a, b in zip(numbers, numbers[1:], strict=False) if a >= b]
    assert not breaks, f"not strictly ascending at {breaks[:5]}"

    assert numbers[0] == EXPECTED_FIRST_NUMBER, (
        f"first PR is #{numbers[0]},predicted #{EXPECTED_FIRST_NUMBER}"
    )

    assert last < PER_PAGE, {f"last page held {last}items-pagination did not reach the tail"}

    assert EXPECTED_TOTAL_LOW <= len(items) <= EXPECTED_TOTAL_HIGH, (
        f"{len(items)}PRs outside the predicted band around 4900"
    )


def assert_filter_is_sound(verdicts, expected_total: int) -> None:
    """Golden assertion for 04 §5 step 2. Written before the first run."""
    assert len(verdicts) == expected_total, (
        f"verdict count {len(verdicts)} != fetched {expected_total}"
    )

    numbers = [v.number for v in verdicts]
    assert len(set(numbers)) == expected_total, "duplicate or missing PR number in verdicts"

    for v in verdicts:
        assert (v.exclusion_reason is None) == v.in_corpus, f"broken verdict: {v}"

    reasons = {v.exclusion_reason for v in verdicts if v.exclusion_reason is not None}
    unreachable = reasons - STEP2_EXCLUSION_REASONS
    assert not unreachable, f"reason unreachable at step 2: {unreachable}"

    kept = sum(1 for v in verdicts if v.in_corpus)
    dropped = sum(1 for v in verdicts if not v.in_corpus)
    assert kept + dropped == expected_total, f"{kept} + {dropped} != {expected_total}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    repo = sys.argv[1] if len(sys.argv) > 1 else "processing/p5.js"

    started = time.time()
    with GitHubClient(os.environ["GITHUB_TOKEN"], repo) as gh:
        fetch = fetch_all(gh)
    elapsed = time.time() - started

    first, last_item = fetch.items[0], fetch.items[-1]
    print(f"\nrepo            {repo}")
    print(f"pages           {fetch.pages} (last held {fetch.last_page_size})")
    print(f"total PRs       {len(fetch.items)}")
    print(f"first           #{first['number']}  {first['created_at']}  {first['user']['login']}")
    print(f"last            #{last_item['number']}  {last_item['created_at']}")
    print(f"elapsed         {elapsed:.0f}s")
    states = Counter(i["state"] for i in fetch.items)
    merged = sum(1 for i in fetch.items if i.get("merged_at"))
    print(f"states          {dict(states)}")
    print(
        f"outcomes        merged={merged} "
        f"closed_unmerged={states['closed'] - merged} open={states['open']}"
    )

    assert_list_is_sound(fetch)
    print("\ngolden assertion PASSED")
