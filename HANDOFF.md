# Handoff — 2026-07-31, Day 8 (tests only; the fetch did not run)

## Done and committed
- ruff format across the tree; spikes/day2 docstrings wrapped, spikes/day5
  import block moved and sorted. `ruff check . && ruff format --check .`
  clean, 31 files.
- ingest/constants.py: BOT_LOGIN_SUFFIX = "[bot]".
- ingest/corpus_filter.py: classify() strips the suffix before the
  BOT_ACCOUNTS lookup (D-P2-9).
- ingest/github_client.py: self._slug derived once in __init__;
  _cache_path renamed _list_cache_path; _diff_cache_path added; fetch_diff
  uses it. from_list_item uses `or GHOST_AUTHOR` / `or "User"` (D-P2-10).
- tests/ moved to the 07 §5 layout: tests/unit/test_corpus_filter.py,
  tests/unit/test_github_client.py.
- tests/fixtures/list_items.json: TWO REAL items from page 1 —
  #16 lmccart merged 2013-07-02, #74 codeanticode unmerged. Deliberately
  NOT prs.json, which 07 §5 reserves for the 5-PR integration corpus.
- pytest tests/unit -q -s: 10 passed. Counter printed and READ:
  {None: 3, bot_author: 2, duplicate_resubmission: 2, housekeeping: 1}.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton 433 MB.
- Neon: schema v001, 6 tables, empty. Migration 002 (judgments.self_authored)
  still unwritten — needed before Phase 5.
- .cache/prs/ holds page 1 of processing/p5.js only. .cache/diffs/ holds
  Day-4 spike artifacts under the OLD naming; the pipeline will not read
  them and does not need to.

## NOT done — Day 8's remaining three quarters
- Full list fetch on processing/p5.js has NOT run.
- apply_corpus_filter has never touched real data.
- D-P2-4 and D-P2-5 remain OPEN; both resolve from that run's logs.

## Read before the fetch
- Predicted: ~49-50 pages, ~4,900 PRs (from 200 UI pages x 25), ~1% of quota.
  Exclusion rate predicted 12% corpus-wide.
- Exclusions will be BACK-LOADED. Page 1 is 2013-2014: no dependabot, no
  allcontributors. Near-zero on the first 10-15 pages is the repo's history,
  not a broken classify(). The 12% is a whole-corpus number.
- Expect FOUR Counter keys: None, bot_author, duplicate_resubmission,
  housekeeping. Both no_source_content (step 4b) and diff_unavailable
  (step 3) are unreachable at step 2. Either appearing means the filter ran
  out of order.
- Golden assertion for the fetch stage, written BEFORE the run:
  no duplicate numbers across all pages, strictly ascending end to end,
  first is #16, last page short, total near 4,900.
- iter_pr_meta() yields PRMeta and DROPS the raw item. PRMeta carries six
  fields; the pull_requests row at 04 §5 step 4 needs body, github_id,
  labels, closed_at, raw. The pipeline script must iterate
  iter_list_pages(), not iter_pr_meta().
- group_duplicates never closes a group, so a 400-600 PR author costs ~1e5
  SequenceMatcher calls. Expect a few SECONDS, not instant. Not a hang.
- normalize_title strips punctuation after whitespace collapse, so a title
  ending " ." keeps a trailing space and misses the normalized-exact branch,
  falling through to the ratio path. Read the D-P2-4 log with that in mind.

## Open decisions carried forward
- D-P2-4 OPEN: "near-identical title". Resolve from the first full fetch.
- D-P2-5 OPEN: housekeeping patterns case-sensitive per 01 §2. Same log.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + asyncpg create_pool() under Cloud Run churn.
  Phase 7. statement_cache_size=0 is the known fallback.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers.
  Rewrite before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 — now a fetch_diff()
  call through the NEW namespaced path. Three requests. Plus p5.js /labels
  confirmed against the actual page.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens, range 64-614,
  median 387. Any anchor written against it says so.
- README at Phase 9 owes FIVE exclusion counts, not four.
- Migration 002 for judgments.self_authored.
- 04 §5 needs a step 3b line for diff_unavailable in the doc revision pass.
- Reserved (CodeDay), Good First Issue, Help Wanted: process labels, NOT
  exclusions.
- fetch_diff raises httpx.HTTPStatusError on any non-406 4xx/5xx. The Day-9
  caller must catch that AND DiffUnavailable — 04 §5 forbids hard-failing
  a run on one PR.
- MAX vs mean-of-top-3: Day-4 evidence exists (p5.js Similar B full-diff
  winner was shared test scaffolding, 0.6788 -> 0.7074). Re-examine at
  Milestone A.

## Decisions log watermark
- Current through D-P2-10, committed. D-P2-8, D-P2-9, D-P2-10 CONFIRMED.
  D-P2-4 and D-P2-5 are the only OPEN Phase 2 entries.

## Next session starts with
- The full list fetch. Everything above under "Read before the fetch" is the
  pre-registration; write the predicted numbers down before running.
- Then apply_corpus_filter over the result. Print the Counter and READ it.
- Then the duplicate groups and housekeeping near-misses: that closes
  D-P2-4 and D-P2-5, and answers whether the [bot] suffix fix changed
  anything on real data.