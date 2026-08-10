"""Area:* label histogram over the frozen PR cache. Zero API calls.

Input to D-P2-21 (corpus-size cut). Throwaway analysis script, not a module.

Two passes:
  1. Run as-is -> full label histogram. Read it, choose the areas.
  2. Fill SELECTED_AREAS with exact names -> distinct-PR union count.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict

from ingest.constants import PR_LIST_CACHE
from ingest.corpus_filter import apply_corpus_filter
from ingest.github_client import from_list_item

PAGE_GLOB = "processing__p5.js_page_*.json"
AREA_PREFIX = "area:"

# Registered before the run (11 §7). Actuals printed alongside.
PREDICTED_DISTINCT_AREAS = "15-30"
PREDICTED_LABELLED_FRACTION = "<15%"
PREDICTED_UNION = "~215 (band 120-400)"
PREDICTED_TOP_AREA = "colour / image"

SELECTED_AREAS: list[str] = []  # pass 2: exact names from pass 1's output


def load_raw_items() -> list[dict]:
    pages = sorted(PR_LIST_CACHE.glob(PAGE_GLOB))
    if not pages:
        raise SystemExit(f"no pages matched {PR_LIST_CACHE / PAGE_GLOB}")

    items: list[dict] = []
    for page in pages:
        with page.open() as fh:
            payload = json.load(fh)
        if not isinstance(payload, list):
            raise SystemExit(f"{page.name}: expected a list, got {type(payload)}")
        items.extend(payload)

    print(f"pages read       : {len(pages)}")
    print(f"raw items        : {len(items)}")

    numbers = [item["number"] for item in items]
    if len(set(numbers)) != len(numbers):
        dupes = [n for n, c in Counter(numbers).items() if c > 1]
        raise SystemExit(f"duplicate PR numbers across pages: {dupes[:10]}")

    return items


def area_labels(item: dict) -> list[str]:
    return [
        label["name"]
        for label in item.get("labels") or []
        if label["name"].lower().startswith(AREA_PREFIX)
    ]


def main() -> None:
    items = load_raw_items()

    verdicts = apply_corpus_filter([from_list_item(item) for item in items])

    # The join is the risk. If from_list_item or the filter drops a PR, a
    # short histogram looks like a finding about p5.js's labelling instead
    # of a bug here. Fail loudly rather than under-report.
    if len(verdicts) != len(items):
        raise SystemExit(f"verdicts {len(verdicts)} != items {len(items)}")
    if {v.number for v in verdicts} != {i["number"] for i in items}:
        raise SystemExit("verdict numbers do not match raw item numbers")

    in_corpus = {v.number for v in verdicts if v.in_corpus}
    print(f"in_corpus        : {len(in_corpus)}")

    counts: Counter[str] = Counter()
    dates: defaultdict[str, list[str]] = defaultdict(list)
    per_pr: list[int] = []
    non_area: Counter[str] = Counter()

    for item in items:
        if item["number"] not in in_corpus:
            continue
        areas = area_labels(item)
        per_pr.append(len(areas))
        for name in areas:
            counts[name] += 1
            dates[name].append(item["created_at"])
        for label in item.get("labels") or []:
            if not label["name"].lower().startswith(AREA_PREFIX):
                non_area[label["name"]] += 1

    labelled = sum(1 for n in per_pr if n > 0)
    total = len(per_pr)
    fraction = labelled / total * 100 if total else 0.0
    mean_per_labelled = sum(per_pr) / labelled if labelled else 0.0

    print()
    print("--- predicted vs actual ---")
    print(f"distinct Area:* labels   predicted {PREDICTED_DISTINCT_AREAS:<18} actual {len(counts)}")
    top = counts.most_common(1)[0][0] if counts else "NONE"
    print(
        f">=1 Area:* label         predicted {PREDICTED_LABELLED_FRACTION:<18}"
        f" actual {fraction:.1f}%  ({labelled}/{total})"
    )
    print(f"top area                 predicted {PREDICTED_TOP_AREA:<18} actual {top}")
    print(f"no Area:* label          : {total - labelled}")
    print(f"mean Area:* per labelled : {mean_per_labelled:.2f}   (>1.0 means the union < the sum)")

    print()
    print("--- Area:* histogram, in_corpus only ---")
    for name, count in counts.most_common():
        span = f"{min(dates[name])[:7]} .. {max(dates[name])[:7]}"
        print(f"{count:5d}  {span}  {name}")

    print()
    print("--- top 15 non-Area labels, for context ---")
    for name, count in non_area.most_common(15):
        print(f"{count:5d}  {name}")

    if not SELECTED_AREAS:
        print()
        print("SELECTED_AREAS empty - fill it from the histogram and re-run for the union.")
        return

    unknown = [name for name in SELECTED_AREAS if name not in counts]
    if unknown:
        raise SystemExit(f"not present in the histogram: {unknown}")

    chosen = set(SELECTED_AREAS)
    union = {
        item["number"]
        for item in items
        if item["number"] in in_corpus and chosen.intersection(area_labels(item))
    }
    naive_sum = sum(counts[name] for name in SELECTED_AREAS)

    print()
    print("--- union over SELECTED_AREAS ---")
    print(f"areas selected   : {len(SELECTED_AREAS)}   (01 §8 floor is 6)")
    print(f"sum of counts    : {naive_sum}")
    print(f"distinct PRs     : {len(union)}   predicted {PREDICTED_UNION}")
    print(f"double-counted   : {naive_sum - len(union)}")


if __name__ == "__main__":
    main()
