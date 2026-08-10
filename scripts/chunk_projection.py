"""Chunk-count projection from the 50 timed diffs. Closes D-P2-21 gate 2.

Zero API calls: reads the diffs the timing run already cached. Same seed,
same sample, so the projection and the timing figure describe one sample.

Run: python -m scripts.chunk_projection
"""

from __future__ import annotations

import os
import random
import statistics
from collections import Counter

from app.retrieval.chunking import is_excluded, parse_hunks
from ingest.corpus_filter import apply_corpus_filter
from ingest.github_client import GitHubClient, from_list_item
from scripts.label_histogram import load_raw_items
from scripts.time_diffs import CORPUS_TOTAL, SAMPLE_SIZE, SEED

EMBEDDING_DIM = 384
BYTES_PER_FLOAT = 4

# MiniLM truncates past 256 tokens (02 §5). The real count needs the real
# tokenizer, which arrives in Phase 3. ~4 bytes/token is a rough English
# heuristic and code tokenizes WORSE than English — more punctuation, more
# subword splits. Treat the truncation figure below as a FLOOR, not a rate.
APPROX_BYTES_PER_TOKEN = 4
TRUNCATION_TOKENS = 256

# Registered before the run.
PREDICTED_CHUNKS_PER_PR = None
PREDICTED_TOTAL_CHUNKS = None
PREDICTED_EXCLUDED_FRAC = None


def main() -> None:
    items = load_raw_items()
    verdicts = apply_corpus_filter([from_list_item(i) for i in items])
    in_corpus = sorted(v.number for v in verdicts if v.in_corpus)

    if len(in_corpus) != CORPUS_TOTAL:
        raise SystemExit(f"in_corpus {len(in_corpus)} != expected {CORPUS_TOTAL}")

    sample = random.Random(SEED).sample(in_corpus, SAMPLE_SIZE)

    # Resolve paths through the client so the naming scheme has one owner.
    # Globbing .cache/diffs/ would sweep up the Day-4 spike files, which use
    # a different scheme and are not in this sample.
    with GitHubClient(os.environ.get("GITHUB_TOKEN", ""), "processing/p5.js") as gh:
        paths = {n: gh._diff_cache_path(n) for n in sample}

    missing = [n for n, p in paths.items() if not p.exists()]
    if missing:
        raise SystemExit(f"{len(missing)} sample diffs not cached: {missing[:5]}")

    per_pr: list[int] = []
    contents: list[int] = []
    zero_hunk: list[int] = []
    ext_counter: Counter[str] = Counter()
    excluded_files = 0
    kept_files = 0

    for number in sample:
        diff = paths[number].read_text()
        hunks = parse_hunks(diff)
        per_pr.append(len(hunks))
        contents.extend(len(h.content) for h in hunks)
        if not hunks:
            zero_hunk.append(number)
        for path in {h.file_path for h in hunks}:
            kept_files += 1
            ext_counter["." + path.rsplit(".", 1)[-1] if "." in path else "(none)"] += 1

    total_chunks = sum(per_pr)
    mean_pr = statistics.mean(per_pr)
    projected = mean_pr * CORPUS_TOTAL
    embed_mb = projected * EMBEDDING_DIM * BYTES_PER_FLOAT / 1e6
    content_mb = statistics.mean(contents) * projected / 1e6 if contents else 0.0

    long_chunks = sum(
        1 for c in contents if c / APPROX_BYTES_PER_TOKEN > TRUNCATION_TOKENS
    )

    print("\n--- predicted vs actual ---")
    print(f"chunks per PR    predicted {PREDICTED_CHUNKS_PER_PR}   actual {mean_pr:.1f}")
    print(f"total at 3685    predicted {PREDICTED_TOTAL_CHUNKS}   actual {projected:,.0f}")
    print(f"excluded frac    predicted {PREDICTED_EXCLUDED_FRAC}   see below")

    print("\n--- chunks in the sample ---")
    print(f"PRs parsed       : {len(sample)}")
    print(f"chunks total     : {total_chunks:,}")
    print(f"per PR mean/med  : {mean_pr:.1f} / {statistics.median(per_pr):.0f}")
    print(f"per PR max       : {max(per_pr)}  (#{sample[per_pr.index(max(per_pr))]})")
    print(f"zero-hunk PRs    : {len(zero_hunk)}  {zero_hunk}")

    print("\n--- projection to 3,685 (invariant 11 premise: ~10k) ---")
    print(f"chunks           : {projected:,.0f}")
    print(f"vs 10k premise   : {projected / 10_000:.1f}x")
    print(f"embeddings       : {embed_mb:.0f} MB   (384 x 4 bytes)")
    print(f"content          : {content_mb:.0f} MB")
    print(f"embed + content  : {embed_mb + content_mb:.0f} MB   (02 §11 target: <250 MB)")

    print("\n--- chunk content sizes ---")
    if contents:
        print(f"mean / median    : {statistics.mean(contents):,.0f} / {statistics.median(contents):,.0f} bytes")
        print(f"largest          : {max(contents):,} bytes")
        pct = long_chunks / len(contents) * 100
        print(f">256 tok (approx): {long_chunks}/{len(contents)} = {pct:.0f}%  FLOOR, not a rate")
        print("                   real figure needs the Phase 3 tokenizer (02 §5)")

    print("\n--- kept file extensions (D-P2-20 input) ---")
    for ext, count in ext_counter.most_common(15):
        print(f"{count:5d}  {ext}")

    print("\n--- exclusion spot-check (03 §2) ---")
    probes = [
        "src/core/main.js", "README.md", "docs/guide.md", "package-lock.json",
        "translations/es.json", ".github/workflows/ci.yml", "test/unit/color.js",
    ]
    for probe in probes:
        print(f"  {'EXCL' if is_excluded(probe) else 'keep'}  {probe}")


if __name__ == "__main__":
    main()