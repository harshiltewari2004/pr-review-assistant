"""Fetch every in_corpus diff to .cache/diffs/. No database writes.

Invariant 19: cache raw before parsing, so every later Phase 2 step is a
local re-run rather than a re-fetch. Resumable by construction — fetch_diff
is cache-first, so re-running skips what is already on disk.

The 406 list written here is the input to step 3's in_corpus = FALSE /
exclusion_reason = 'diff_unavailable' marking, once pull_requests exists.

Run: python -m scripts.warm_diff_cache
"""

from __future__ import annotations

import json
import logging
import os
import time

import httpx
from dotenv import load_dotenv

from ingest.constants import CACHE_ROOT
from ingest.corpus_filter import apply_corpus_filter
from ingest.github_client import DiffUnavailable, GitHubClient, from_list_item
from scripts.label_histogram import load_raw_items

CORPUS_TOTAL = 3685
STATUS_PATH = CACHE_ROOT / "diff_fetch_status.json"
CHECKPOINT_EVERY = 50

# Registered before the run.
PREDICTED_406 = None
PREDICTED_MINUTES = 97
PREDICTED_OTHER_ERRORS = None

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    load_dotenv()

    items = load_raw_items()
    verdicts = apply_corpus_filter([from_list_item(i) for i in items])
    in_corpus = sorted(v.number for v in verdicts if v.in_corpus)

    if len(in_corpus) != CORPUS_TOTAL:
        raise SystemExit(f"in_corpus {len(in_corpus)} != expected {CORPUS_TOTAL}")

    unavailable: list[int] = []
    errors: list[dict] = []
    fetched = 0
    from_cache = 0
    start = time.perf_counter()

    def checkpoint() -> None:
        # Written incrementally: a crash at PR 3000 must not lose the 406
        # list, which is the only artifact of this run that is not a file
        # on disk already.
        STATUS_PATH.write_text(
            json.dumps(
                {
                    "corpus_total": CORPUS_TOTAL,
                    "diff_unavailable": unavailable,
                    "errors": errors,
                    "completed": fetched + from_cache + len(unavailable) + len(errors),
                },
                indent=2,
            )
        )

    with GitHubClient(os.environ["GITHUB_TOKEN"], "processing/p5.js") as gh:
        for i, number in enumerate(in_corpus, 1):
            was_cached = gh._diff_cache_path(number).exists()
            try:
                gh.fetch_diff(number)
            except DiffUnavailable:
                unavailable.append(number)
                print(f"{i:5d}/{CORPUS_TOTAL}  #{number:<6} 406 diff_unavailable")
            except httpx.HTTPStatusError as exc:
                # 04 §5 forbids hard-failing the run on one PR. RuntimeError
                # from github_client is deliberately NOT caught — five
                # consecutive 403s means the quota is gone, which is a
                # run-level failure, not a per-PR one.
                errors.append({"number": number, "status": exc.response.status_code})
                print(f"{i:5d}/{CORPUS_TOTAL}  #{number:<6} HTTP {exc.response.status_code}")
            else:
                if was_cached:
                    from_cache += 1
                else:
                    fetched += 1

            if i % CHECKPOINT_EVERY == 0:
                checkpoint()
                elapsed = time.perf_counter() - start
                rate = elapsed / i
                remaining = (CORPUS_TOTAL - i) * rate / 60
                print(
                    f"{i:5d}/{CORPUS_TOTAL}  {elapsed / 60:.1f}m elapsed  "
                    f"~{remaining:.0f}m left  406s={len(unavailable)}  "
                    f"errors={len(errors)}  requests={gh.requests_made}"
                )

        requests_made = gh.requests_made

    checkpoint()
    wall = time.perf_counter() - start

    print("\n--- predicted vs actual ---")
    print(f"406 count        predicted {PREDICTED_406}   actual {len(unavailable)}")
    print(f"minutes          predicted {PREDICTED_MINUTES}   actual {wall / 60:.0f}")
    print(f"other errors     predicted {PREDICTED_OTHER_ERRORS}   actual {len(errors)}")

    print("\n--- run ---")
    print(f"wall clock       : {wall / 60:.1f} min")
    print(f"fetched / cached : {fetched} / {from_cache}")
    print(f"406 / other      : {len(unavailable)} / {len(errors)}")
    print(f"requests_made    : {requests_made}   (expect ~{fetched})")
    print(f"status written   : {STATUS_PATH}")

    if unavailable:
        rate = len(unavailable) / CORPUS_TOTAL * 100
        print(f"\n406 rate         : {len(unavailable)}/{CORPUS_TOTAL} = {rate:.1f}%")
        print("                   -> exclusion_reason = 'diff_unavailable' at step 3")
    if errors:
        print(f"\nerrors           : {errors[:20]}")


if __name__ == "__main__":
    main()