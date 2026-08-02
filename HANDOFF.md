# Handoff — 2026-08-01, Day 9 (step 1 done; the filter did not run)

## Done and committed
- scripts/index_repo.py created — 04 §5 step 1 only. fetch_all() drives
  iter_list_pages() and keeps RAW items (iter_pr_meta drops body,
  github_id, labels, closed_at, raw — 02 §4 needs all five).
- assert_list_is_sound(): no duplicate numbers, strictly ascending,
  first == #16, last page short, total within band. Teeth-checked —
  watched it FAIL at 4,400-5,400, then pass at 4,300-4,450.
- ingest/constants.py: EXPECTED_FIRST_NUMBER / _TOTAL_LOW / _TOTAL_HIGH.
  scripts/index_repo.py imports them; local copies deleted (they shadowed).
- ingest/github_client.py: fetch_diff now calls _diff_cache_path(number).
  It was defined and never called — bare-number path would have returned
  a Day-4 FastAPI diff for a colliding p5.js number, silently.

## Measured — the corpus is real now
- 4,370 PRs, 44 pages, last page 70 items, #16 (2013-07-02) → #9029.
- state split: closed 4246/open 124.
- outcome split: merged 3558/closed_unmerged 688/open 124.Sums to 4370
- Cold 96s / 44 requests. Warm 3s / 1 request (page 44 only, D-P2-6).
- .cache/prs/ now holds all 44 pages of processing/p5.js.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton 433 MB.
- Neon: schema v001, 6 tables, EMPTY. Nothing has been written to Postgres.
- Migration 002 (judgments.self_authored) still unwritten — before Phase 5.

## NOT done
- apply_corpus_filter has still never touched real data.
- D-P2-4 and D-P2-5 remain OPEN. Both resolve from that run, which needs
  ZERO network — everything is on disk.
- Nothing has been written to pull_requests. Phase 2's deliverable is
  "pull_requests populated for the full repo" and the table is empty.

## Read before the filter run
- Expect FOUR Counter keys: None, bot_author, duplicate_resubmission,
  housekeeping. no_source_content (4b) and diff_unavailable (step 3) are
  unreachable at step 2 — either appearing means the filter ran out of order.
- Exclusions are BACK-LOADED. Pages 1-15 are 2013-2015: no dependabot, no
  allcontributors. Near-zero there is the repo's history, not a broken
  classify(). The 12% prediction is whole-corpus.
- group_duplicates never closes a group: a 400-600 PR author costs ~1e5
  SequenceMatcher calls. Seconds, not a hang. Time it — the 7-day window
  is the cheapest of the three predicates and currently runs last.
- normalize_title strips punctuation after whitespace collapse, so a title
  ending " ." keeps a trailing space and misses the normalized-exact branch.
  Read the D-P2-4 log with that in mind.
- Golden assertion for the filter stage, to write BEFORE the run:
  in_corpus count + sum of exclusion counts == 4,370 exactly; every excluded
  row has a non-null exclusion_reason; no reason outside the four literals.

## Field audit carried forward — 02 §4
Fourteen of seventeen columns fill from a list item. THREE DO NOT:
files_changed, additions, deletions. All have DB defaults, so a bad insert
raises nothing. files_changed carries the file-overlap signal (03 §1) and
is GIN-indexed — defaulting it to '{}' would zero one of three signals
corpus-wide and still look fine. Source is the parsed diff at step 4, free.
Open sub-question: does files_changed record every file in the diff, or
only files surviving 03 §2's exclusions? Not equivalent — a PR touching
p5.Renderer.js + CHANGELOG.md would Jaccard against every changelog PR
under the first reading. Log as D-P2-14 before step 4 is written.

## Open decisions carried forward
- D-P2-4 OPEN: "near-identical title". Resolves from the filter run.
- D-P2-5 OPEN: housekeeping patterns case-sensitive per 01 §2. Same run.
- D-P2-12 OPEN: LIST_STATE = "all" admits open PRs. Phase 4.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
  statement_cache_size=0 is the known fallback.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers.
  Rewrite before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 through the NEW
  namespaced fetch_diff path. Three requests. Plus p5.js /labels confirmed.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens, range 64-614,
  median 387. Any anchor written against it says so.
- README at Phase 9 owes FIVE exclusion counts, not four.
- Migration 002 for judgments.self_authored.
- 04 §5 needs a step 3b line for diff_unavailable in the doc revision pass.
- Reserved (CodeDay), Good First Issue, Help Wanted: process labels, NOT
  exclusions.
- fetch_diff raises httpx.HTTPStatusError on any non-406 4xx/5xx. The
  step-3 caller must catch that AND DiffUnavailable — 04 §5 forbids
  hard-failing a run on one PR.
- MAX vs mean-of-top-3: Day-4 evidence exists (p5.js Similar B full-diff
  winner was shared test scaffolding, 0.6788 -> 0.7074). Milestone A.
- Six doc revisions for the Cloud Run pivot: 04, 05, 08.

## Decisions log watermark
- Current through D-P2-13, committed. OPEN: D-P2-4, D-P2-5, D-P2-12.

## Next session starts with
- apply_corpus_filter over all 4,370 cached items. Zero network.
- Write the filter stage's golden assertion BEFORE running it.
- Print the Counter and READ it. Then duplicate groups and housekeeping
  near-misses — that closes D-P2-4 and D-P2-5, and answers whether the
  [bot] suffix fix changed anything on real data.
- Then step 4 field-fill decision (D-P2-14) before any insert.

## Schedule
- Day 9 of 50. 09 §3 puts diff_parser.py at 11-12 and index_repo wiring
  at 13. Phase 2's deliverable is a populated pull_requests table; it is
  still empty. Do not let the filter run slide into the parser days.