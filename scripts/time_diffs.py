"""Timing sample for step 3. Closes D-P2-21's gate 1. Throwaway.

Fetches diffs for a fixed random sample of in_corpus PRs and reports
seconds-per-diff, the 406 rate, and byte sizes. Predictions are registered
in JOURNAL.md before this runs (11 §7).

Run: python -m scripts.time_diffs
"""

from __future__ import annotations

import logging
import os
import random
import statistics
import time

import httpx
from dotenv import load_dotenv

from ingest.corpus_filter import apply_corpus_filter
from ingest.github_client import DiffUnavailable, GitHubClient, from_list_item

# Reusing the loader rather than redefining it. Both are throwaway scripts;
# when step 3 lands properly in index_repo.py this import goes away.
from scripts.label_histogram import load_raw_items

SAMPLE_SIZE = 50
SEED = 20260808  # fixed: the sample must be reproducible
CORPUS_TOTAL = 3685

# Registered before the run.
PREDICTED_MEAN_S = None  # fill in
PREDICTED_TOTAL_MIN = 60  # 3685 * predicted mean, in minutes
PREDICTED_406 = None  # fill in
PREDICTED_REQUESTS = 50

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv()

    items = load_raw_items()
    verdicts = apply_corpus_filter([from_list_item(i) for i in items])
    in_corpus = sorted(v.number for v in verdicts if v.in_corpus)

    if len(in_corpus) != CORPUS_TOTAL:
        raise SystemExit(f"in_corpus {len(in_corpus)} != expected {CORPUS_TOTAL}")

    sample = random.Random(SEED).sample(in_corpus, SAMPLE_SIZE)
    print(f"\nsample of {len(sample)} from {len(in_corpus)}, seed {SEED}")
    print(f"first five: {sample[:5]}\n")

    durations: list[float] = []
    sizes: list[int] = []
    unavailable: list[int] = []
    http_errors: list[tuple[int, int]] = []

    with GitHubClient(os.environ["GITHUB_TOKEN"], "processing/p5.js") as gh:
        if gh._diff_cache_path(sample[0]).exists():
            raise SystemExit("sample PR already cached - timing would measure disk")

        wall_start = time.perf_counter()
        for i, number in enumerate(sample, 1):
            start = time.perf_counter()
            try:
                diff = gh.fetch_diff(number)
            except DiffUnavailable:
                # 406: GitHub will not generate a diff. Mark and continue (D-P2-2).
                durations.append(time.perf_counter() - start)
                unavailable.append(number)
                print(f"{i:3d}/{SAMPLE_SIZE}  #{number:<6} 406 diff_unavailable")
                continue
            except httpx.HTTPStatusError as exc:
                # 04 §5 forbids hard-failing the run on one PR.
                durations.append(time.perf_counter() - start)
                http_errors.append((number, exc.response.status_code))
                print(f"{i:3d}/{SAMPLE_SIZE}  #{number:<6} HTTP {exc.response.status_code}")
                continue

            elapsed = time.perf_counter() - start
            durations.append(elapsed)
            sizes.append(len(diff))
            print(f"{i:3d}/{SAMPLE_SIZE}  #{number:<6} {elapsed:6.2f}s  {len(diff):>9,} bytes")

        wall = time.perf_counter() - wall_start
        requests_made = gh.requests_made

    ok = len(sizes)
    mean = statistics.mean(durations)
    median = statistics.median(durations)
    slowest = max(durations)

    print("\n--- predicted vs actual ---")
    print(f"mean s/diff      predicted {PREDICTED_MEAN_S}   actual {mean:.2f}")
    print(
        f"3685 wall (min)  predicted {PREDICTED_TOTAL_MIN}"
        f"           actual {mean * CORPUS_TOTAL / 60:.0f}"
    )
    print(f"406 count        predicted {PREDICTED_406}   actual {len(unavailable)}")
    print(f"requests_made    predicted {PREDICTED_REQUESTS}   actual {requests_made}")

    print("\n--- timing ---")
    print(f"wall clock       : {wall:.1f}s for {SAMPLE_SIZE}")
    print(f"mean / median    : {mean:.2f}s / {median:.2f}s")
    print(f"slowest          : {slowest:.2f}s")
    print(f"delay floor      : 0.75s  ({0.75 / mean * 100:.0f}% of mean)")
    print(f"3685 projection  : {mean * CORPUS_TOTAL / 3600:.2f} hours")

    print("\n--- outcomes ---")
    print(f"ok / 406 / other : {ok} / {len(unavailable)} / {len(http_errors)}")
    if unavailable:
        print(f"406 PRs          : {unavailable}")
        rate = len(unavailable) / SAMPLE_SIZE
        print(f"406 rate         : {rate * 100:.0f}%  -> ~{rate * CORPUS_TOTAL:.0f} of 3685")
    if http_errors:
        print(f"other errors     : {http_errors}")

    if sizes:
        print("\n--- diff sizes (gate 2 input) ---")
        print(
            f"mean / median    : {statistics.mean(sizes):,.0f}"
            f"/ {statistics.median(sizes):,.0f} bytes"
        )
        print(f"largest          : {max(sizes):,} bytes")
        print(
            f"3685 projection  : {statistics.mean(sizes) * CORPUS_TOTAL / 1e6:.0f} MB of raw diff"
        )


if __name__ == "__main__":
    main()
