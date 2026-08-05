"""D-P2-12b — grouping diff for D-P2-4's correction. Day 12.

Runs production group_duplicates() twice against the FROZEN cache: once as
shipped (normalized-exact), once with the deleted 0.95 SequenceMatcher branch
restored via monkeypatch. Diffs the two groupings.

Answers: dropping the ratio branch removed 10 anchor-ratio members but only 9
exclusions and 7 groups. The hypothesis is that grouping is greedy and
order-dependent, so dissolving a group RELEASES its members and one new group
formed from them.

NO NETWORK. Does not import GitHubClient. Does not call fetch_all(). Reading
the cache is the point — fetch_all() re-fetches the short final page and would
drift the corpus mid-analysis (D-P2-15).

The ratio branch is restored HERE ONLY. ingest/ is not touched.
"""

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ingest import corpus_filter  # noqa: E402
from ingest.corpus_filter import classify, group_duplicates, normalize_title  # noqa: E402
from ingest.github_client import from_list_item  # noqa: E402

# D-P2-4 deleted TITLE_SIMILARITY_THRESHOLD from ingest/constants.py.
# Resurrected here as a local literal for the comparison run only.
RATIO_THRESHOLD = 0.95

CACHE_DIR = REPO_ROOT / ".cache" / "prs"
CACHE_GLOB = "processing__p5.js_page_*.json"  # NOT *.json — other repos may be cached
PAGE_RE = re.compile(r"_page_(\d+)\.json$")
EXPECTED_TOTAL = 4372  # frozen corpus as of the Day-11 run. A mismatch = drift.

PREDICTION = """
REGISTERED PREDICTION (Day 12, before running)
  B (ratio restored) : 63 groups, 69 exclusions, anchor-branch exact=59 ratio=10
  A (as shipped)     : 56 groups, 60 exclusions
  wholly dissolved   : 8
  shrunk but survived: 2
  NEWLY CREATED      : 1  <- the claim under test
  created group's members trace back to a dissolved group
If created == 0, the order-dependence model is wrong and the -7/-9 deltas
need a different explanation.
"""


def load_metas():
    """Read cached list pages in production order: page number ASCENDING."""

    def page_num(p: Path) -> int:
        m = PAGE_RE.search(p.name)
        if not m:
            raise ValueError(f"unparseable cache filename: {p.name}")
        return int(m.group(1))

    files = sorted(CACHE_DIR.glob(CACHE_GLOB), key=page_num)
    assert files, f"no cache pages matched {CACHE_GLOB} in {CACHE_DIR}"
    print(f"cache pages: {len(files)}  first={files[0].name}  last={files[-1].name}")

    items = []
    for f in files:
        items.extend(json.loads(f.read_text()))

    metas = [from_list_item(i) for i in items]

    # Golden assertions for the spike itself. 07 §3 — the stage has teeth or
    # it is not finished.
    assert len(metas) == EXPECTED_TOTAL, (
        f"CACHE DRIFTED: {len(metas)} PRs, expected {EXPECTED_TOTAL}. "
        "The comparison baseline is gone. Stop and resolve D-P2-15 first."
    )
    numbers = [m.number for m in metas]
    assert len(set(numbers)) == len(numbers), "duplicate PR numbers in cache"
    assert numbers == sorted(numbers), "cache pages not in ascending order"
    print(f"loaded {len(metas)} PRs, strictly ascending, #{numbers[0]}..#{numbers[-1]}\n")
    return metas


def titles_match_with_ratio(a: str, b: str) -> bool:
    """The pre-D-P2-4 implementation, verbatim."""
    na, nb = normalize_title(a), normalize_title(b)
    if na == nb:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= RATIO_THRESHOLD


def run_grouping(survivors, *, with_ratio: bool):
    """group_duplicates() resolves titles_match at call time from module
    globals, so patching the module attribute swaps the branch.

    VERIFY THIS HOLDS: if group_duplicates does not call titles_match by bare
    name, this patch is a silent no-op and B == A for the wrong reason.
    """
    original = corpus_filter.titles_match
    if with_ratio:
        corpus_filter.titles_match = titles_match_with_ratio
    try:
        return group_duplicates(survivors)
    finally:
        corpus_filter.titles_match = original


def summarize(groups, label):
    sets = [frozenset(m.number for m in g) for g in groups]
    assert all(len(s) >= 2 for s in sets), f"{label}: singleton returned as a group"
    exclusions = sum(len(s) - 1 for s in sets)
    print(
        f"{label}: {len(sets)} groups, {exclusions} exclusions, {sum(len(s) for s in sets)} members"
    )
    return sets


def branch_tally(groups):
    """Anchor-based tally, matching the 2026-08-02 evidence script exactly so
    the numbers are comparable to the 59/10 already in DECISIONS.md."""
    exact = ratio = 0
    for g in groups:
        anchor = g[0]
        for m in g[1:]:
            if normalize_title(anchor.title) == normalize_title(m.title):
                exact += 1
            else:
                ratio += 1
    return exact, ratio


def main():
    print(PREDICTION)

    metas = load_metas()
    survivors = [m for m in metas if classify(m) is None]
    print(f"survivors of classify(): {len(survivors)}\n")

    groups_b = run_grouping(survivors, with_ratio=True)
    groups_a = run_grouping(survivors, with_ratio=False)

    sets_b = summarize(groups_b, "B (ratio restored)")
    sets_a = summarize(groups_a, "A (as shipped)   ")

    if sets_a == sets_b:
        print(
            "\n!!! B is identical to A. Either the monkeypatch never took "
            "(group_duplicates does not call module-level titles_match), or "
            "the ratio branch genuinely did nothing. Check the seam before "
            "reading anything below as a result.\n"
        )

    exact, ratio = branch_tally(groups_b)
    print(f"B anchor-branch tally: exact={exact}  ratio-only={ratio}")
    print("  (DECISIONS.md D-P2-4 recorded exact=59 ratio-only=10)\n")

    set_a, set_b = set(sets_a), set(sets_b)
    by_number_a = {n: s for s in sets_a for n in s}

    dissolved, shrunk = [], []
    for b in sets_b:
        if b in set_a:
            continue
        survivor = next((a for a in sets_a if a < b), None)
        (shrunk if survivor else dissolved).append((b, survivor))

    created = [a for a in sets_a if a not in set_b and not any(a < b for b in sets_b)]

    print(f"identical in both : {len(set_a & set_b)}")
    print(f"wholly dissolved  : {len(dissolved)}")
    print(f"shrunk, survived  : {len(shrunk)}")
    print(f"NEWLY CREATED     : {len(created)}\n")

    for b, _ in sorted(dissolved, key=lambda x: min(x[0])):
        print(f"  dissolved  {sorted(b)}")
    for b, a in sorted(shrunk, key=lambda x: min(x[0])):
        print(f"  shrunk     {sorted(b)}  ->  {sorted(a)}")

    print()
    for a in created:
        print(f"  CREATED    {sorted(a)}")
        for n in sorted(a):
            prior = next((b for b in sets_b if n in b), None)
            origin = f"was in B group {sorted(prior)}" if prior else "was ungrouped in B"
            print(f"    #{n}: {origin}")
            title = next(m.title for m in survivors if m.number == n)
            print(f"         title {title!r}  (now grouped as {sorted(by_number_a[n])})")

    print("\n--- reconciliation")
    print(f"  delta groups     {len(sets_a) - len(sets_b):+d}")
    print(
        f"  delta exclusions {sum(len(s) - 1 for s in sets_a) - sum(len(s) - 1 for s in sets_b):+d}"
    )
    print(f"  delta members    {sum(len(s) for s in sets_a) - sum(len(s) for s in sets_b):+d}")


if __name__ == "__main__":
    main()
