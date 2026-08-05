"""GitHub REST client for the local indexing pipeline (04 §5 steps 1 and 3).

Every raw response is written to .cache/ BEFORE any parsing (hot invariant 19).
Imported only by scripts/ — never by app/ (04 §3).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from ingest.constants import (
    BACKOFF_BASE_S,
    DIFF_CACHE,
    DIFF_MEDIA_TYPE,
    GHOST_AUTHOR,
    GITHUB_API_ROOT,
    GITHUB_API_VERSION,
    INTER_REQUEST_DELAY_S,
    LIST_DIRECTION,
    LIST_SORT,
    LIST_STATE,
    MAX_BACKOFF_ATTEMPTS,
    PER_PAGE,
    PR_LIST_CACHE,
    RATE_LIMIT_FLOOR,
    RATE_LIMIT_SLEEP_BUFFER_S,
)
from ingest.corpus_filter import PRMeta  # contract direction: client -> filter

log = logging.getLogger(__name__)


class DiffUnavailable(Exception):
    """GitHub cannot produce this diff. Terminal, not a transport failure."""

    def __init__(self, number: int, status: int) -> None:
        super().__init__(f"PR #{number}: diff unavailable (HTTP {status})")
        self.number = number
        self.status = status


class CacheFrozen(RuntimeError):
    """The list cache carries a freeze manifest (D-P2-15). Fetching is refused."""


def _parse_ts(value: str | None) -> datetime | None:
    """GitHub sends '2026-07-29T14:02:11Z'.

    fromisoformat accepts the trailing Z from 3.11 onward (06 §1 pins 3.11)
    and returns tz-aware UTC — which is what corpus_filter's 7-day duplicate
    window compares against. A naive datetime raises on that comparison.
    """
    if value is None:
        return None
    return datetime.fromisoformat(value)


def from_list_item(item: dict[str, Any]) -> PRMeta:
    """One /pulls list item -> PRMeta.

    Lives here and not in corpus_filter: the filter must not know GitHub's
    JSON key names (HANDOFF 2026-07-29, sequencing note).
    """
    # user is null on PRs from deleted accounts. A ten-year-old repository has
    # them, and the failure is a NoneType attribute error rather than a
    # KeyError — `item["user"]["login"]` would not have raised the error the
    # golden assertion was written to catch.
    user = item.get("user") or {}
    return PRMeta(
        number=item["number"],
        title=item["title"],
        author=user.get("login") or GHOST_AUTHOR,
        # 'Organization' is a third real value alongside User and Bot. It is
        # not a bot; 07 §4's account list and step 4b handle the rest.
        author_type=user.get("type") or "User",
        created_at=_parse_ts(item["created_at"]),
        merged_at=_parse_ts(item.get("merged_at")),
    )


class GitHubClient:
    def __init__(self, token: str, repo: str, refresh: bool = False) -> None:
        self.repo = repo
        self.refresh = refresh
        self._slug = repo.replace("/", "__")
        self._client = httpx.Client(
            base_url=GITHUB_API_ROOT,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
            timeout=30.0,
        )

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self._client.close()

    def _request(
        self, path: str, *, accept: str | None = None, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """One request, with rate-limit respect and backoff on 403/429.

        Returns the response for every non-retryable status, 406 included.
        This layer decides only what is worth retrying; callers decide what a
        status means.
        """
        headers = {"Accept": accept} if accept else None
        for attempt in range(MAX_BACKOFF_ATTEMPTS):
            resp = self._client.get(path, params=params, headers=headers)
            self._respect_rate_limit(resp)
            if resp.status_code in (403, 429):
                # GitHub returns 403, not 429, on secondary rate limits, and
                # sometimes supplies Retry-After. Honour it when present.
                wait = float(resp.headers.get("Retry-After", BACKOFF_BASE_S**attempt))
                log.warning(
                    "retryable status %s on %s; sleeping %.1fs", resp.status_code, path, wait
                )
                time.sleep(wait)
                continue
            time.sleep(INTER_REQUEST_DELAY_S)
            return resp
        # Run-level, not PR-level: five consecutive 403s means the quota is
        # gone, which is not something to log and continue past.
        raise RuntimeError(f"gave up on {path} after {MAX_BACKOFF_ATTEMPTS} attempts")

    def _respect_rate_limit(self, resp: httpx.Response) -> None:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is None or int(remaining) >= RATE_LIMIT_FLOOR:
            return
        reset_at = int(resp.headers["X-RateLimit-Reset"])
        sleep_for = max(0.0, reset_at - time.time() + RATE_LIMIT_SLEEP_BUFFER_S)
        log.warning("rate-limit floor reached (%s left); sleeping %.0fs", remaining, sleep_for)
        time.sleep(sleep_for)

    def _list_cache_path(self, page: int) -> Path:
        return PR_LIST_CACHE / f"{self._slug}_page_{page:04d}.json"

    def _manifest_path(self) -> Path:
        return PR_LIST_CACHE / f"{self._slug}_MANIFEST.json"

    def read_manifest(self) -> dict[str, Any] | None:
        path = self._manifest_path()
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _read_cached_page(self, page: int) -> list[dict[str, Any]] | None:
        if self.refresh:
            return None
        path = self._list_cache_path(page)
        if not path.exists():
            return None
        items = json.loads(path.read_text())
        # Only a FULL page is immutable under direction=asc. A short page is
        # the tail and may have been partial when cached, so it is never
        # trusted (D-P2-6).
        return items if len(items) == PER_PAGE else None

    def _fetch_list_page(self, page: int) -> list[dict[str, Any]]:
        resp = self._request(
            f"/repos/{self.repo}/pulls",
            params={
                "state": LIST_STATE,
                "sort": LIST_SORT,
                "direction": LIST_DIRECTION,
                "per_page": PER_PAGE,
                "page": page,
            },
        )
        resp.raise_for_status()
        path = self._list_cache_path(page)
        path.write_text(resp.text)
        # Read back from disk rather than using resp.json(): the cache is the
        # source of truth downstream (04 §5), so a failed write must surface
        # here and not three stages later.
        return json.loads(path.read_text())

    def _iter_frozen_pages(
        self, manifest: dict[str, Any]
    ) -> Iterator[tuple[int, list[dict[str, Any]]]]:
        """Serve the frozen snapshot from disk. Issues zero requests.

        Deliberately bypasses _read_cached_page: that method never trusts a
        short final page (D-P2-6), which is correct mid-fetch and is what
        re-fetched page 44 on every run and drifted the corpus three times
        (D-P2-15).

        Verifies the whole snapshot BEFORE yielding anything, so a caller
        cannot consume half a corpus and then be told it was wrong.
        """

        expected_pages = manifest["pages"]
        pages: list[tuple[int, list[dict[str, Any]]]] = []
        total = 0

        for page in range(1, expected_pages + 1):
            path = self._list_cache_path(page)
            if not path.exists():
                raise CacheFrozen(f"manifest expects page {page}; missing {path}")
            items = json.loads(path.read_text())
            pages.append((page, items))
            total += len(items)

        stray = self._list_cache_path(expected_pages + 1)
        if stray.exists():
            raise CacheFrozen(
                f"manifest says {expected_pages} pages but {stray} exists — "
                "the cache was written to after the freeze"
            )

        if total != manifest["total_prs"]:
            raise CacheFrozen(
                f"frozen cache holds {total} PRs; manifest says {manifest['total_prs']}"
            )

        yield from pages

    def iter_list_pages(self) -> Iterator[tuple[int, list[dict[str, Any]]]]:
        """Yield (page_number, raw_items) for every /pulls page, cache-first.

        Resumability is page-level and rests on direction=asc: under GitHub's
        default created-descending order, every PR opened between an
        interrupted run and its resume shifts the pagination window, so page 3
        from yesterday and page 3 from today describe different PRs. Ascending
        order makes a full page's contents permanent; new PRs land on the tail.

        When a freeze manifest is present the cache is served whole from disk
        and no request is issued (D-P2-15).
        """

        manifest = self.read_manifest()
        if manifest is not None:
            if self.refresh:
                raise CacheFrozen(
                    "--refresh against a frozen cache. Thaw deliberately: "
                    "python -m scripts.freeze_cache --thaw"
                )
            yield from self._iter_frozen_pages(manifest)
            return

        PR_LIST_CACHE.mkdir(parents=True, exist_ok=True)
        page = 1
        while True:
            items = self._read_cached_page(page)
            if items is None:
                items = self._fetch_list_page(page)
            if not items:
                return
            yield page, items
            if len(items) < PER_PAGE:
                return
            page += 1

    def iter_pr_meta(self) -> Iterator[PRMeta]:
        for _page, items in self.iter_list_pages():
            for item in items:
                yield from_list_item(item)

    def _diff_cache_path(self, number: int) -> Path:
        """Namespaced by repo: the Day-4 spike left bare-number FastAPI diffs
        in .cache/diffs/, and p5.js PR numbers will eventually reach them.
        A wrong cache hit returns another repo's diff and does not raise.
        """
        return DIFF_CACHE / f"{self._slug}_{number}.diff"

    def fetch_diff(self, number: int) -> str:
        """Raw unified diff for one PR, cache-first.

        Raises DiffUnavailable on 406 — GitHub will not generate a diff past
        ~20k lines / 300 files. The caller marks in_corpus = FALSE with
        exclusion_reason = 'diff_unavailable' and continues (D-P2-2).
        """
        DIFF_CACHE.mkdir(parents=True, exist_ok=True)
        path = self._diff_cache_path(number)
        if path.exists() and not self.refresh:
            return path.read_text()

        resp = self._request(f"/repos/{self.repo}/pulls/{number}", accept=DIFF_MEDIA_TYPE)
        if resp.status_code == 406:
            raise DiffUnavailable(number, resp.status_code)
        resp.raise_for_status()
        path.write_text(resp.text)  # write before any parse (invariant 19)
        return path.read_text()


if __name__ == "__main__":
    import os
    import sys

    logging.basicConfig(level=logging.INFO)
    repo = sys.argv[1] if len(sys.argv) > 1 else "processing/p5.js"
    with GitHubClient(os.environ["GITHUB_TOKEN"], repo) as gh:
        page, items = next(gh.iter_list_pages())
        assert len(items) == PER_PAGE, f"expected {PER_PAGE} items,got {len(items)}"
        metas = [from_list_item(i) for i in items]

        # The premise of page-level resumability, asserted rather than assumed.
        assert metas[0].created_at < metas[-1].created_at, "direction = asc not applied"
        print(f"page{page}:{len(metas)}items")
        print(metas[0])
        print(metas[-1])
