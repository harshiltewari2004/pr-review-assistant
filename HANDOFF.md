# Handoff — 2026-08-02, Day 10 (the filter ran; the fix from it has NOT landed)

## Done and committed
- scripts/index_repo.py: assert_filter_is_sound() — four independent checks
  (count vs fetch total, unique numbers, paired invariant, reasons subset of
  STEP2_EXCLUSION_REASONS). Teeth-checked from /tmp, all four watched failing.
- ingest/constants.py: STEP2_EXCLUSION_REASONS (three literals).
  EXCLUSION_DIFF_UNAVAILABLE renamed REASON_DIFF_UNAVAILABLE and MOVED UP into
  the literals block — it was defined 60 lines below the frozenset reading it.
- ingest/corpus_filter.py: normalize_title() ends in .strip().
- load_dotenv() at the top of __main__. Third GITHUB_TOKEN KeyError of the project.
- Step 2 wired into __main__ AFTER step 1's assertion, per 04 §5 ordering.

## Measured — step 2 has touched real data
- 4,371 PRs (up from 4,370 — see D-P2-15). 44 pages, last 71, #16 -> #9031.
- Counter: {None: 3666, bot_author: 625, duplicate_resubmission: 69, housekeeping: 11}
- in_corpus 3,666. Exclusions 705 = 16.1%. Four keys only; no step-3 or step-4b
  reason appeared, so the ordering held.
- Predictions were 400 / 36 / 84. Largest-category call correct.
- 63 duplicate groups, branch tally exact=59 ratio-only=10.
- Housekeeping near-misses: ZERO across the whole corpus.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton 433 MB.
- Neon: schema v001, 6 tables, EMPTY. Nothing written to Postgres.
- Migration 002 (judgments.self_authored) still unwritten — before Phase 5.

## NEXT SESSION STARTS HERE — the D-P2-4 fix
The filter currently excludes FOUR MERGED PRs (#2780, #2781, #4409, #4369) as
duplicate resubmissions. Verified on GitHub; all are distinct work. Nothing
downstream consumes this yet (pull_requests is empty), so it is not urgent —
but it must land before any insert.

1. titles_match(): delete the SequenceMatcher branch, return na == nb only.
   Remove TITLE_SIMILARITY_THRESHOLD from constants.py and the difflib import —
   dead, not commented out. grep both names after.
2. Update tests/unit/test_corpus_filter.py — any test asserting a ratio match
   should now assert the pair does NOT group.
3. Re-run. PREDICTED: 55 groups, 59 exclusions, in_corpus 3,676, total 695.
   That prediction is registered in DECISIONS.md — read the actual against it.
4. Then step 4 field-fill decision (D-P2-14) before any insert.

## Read before the next run
- assert_filter_is_sound RUNS but PRINTS NOTHING on success. Two lines are still
  missing from __main__: `filter elapsed` and `print("\nfilter golden assertion
  PASSED")`. Silence standing in for success is what invariant 20 exists to stop.
- The evidence scripts are gone (/tmp, deliberately). To regenerate the branch
  attribution, rebuild: classify() -> survivors -> group_duplicates() ->
  per member compare normalize_title(anchor) vs normalize_title(member).
  Compare to group[0], NOT the keeper — the window is anchored to the first
  member.
- python-dotenv resolves relative to the CALLING FILE. A scratch script outside
  the repo needs load_dotenv("/Users/harshiltewari/pr-review-assistant/.env").

## Field audit carried forward — 02 §4
Fourteen of seventeen columns fill from a list item. THREE DO NOT:
files_changed, additions, deletions. All have DB defaults, so a bad insert
raises nothing. All three source from the parsed diff at step 4. One question,
not three: every file in the diff, or only files surviving 03 §2? Logged as
D-P2-14; resolve before step 4 is written.

## Open decisions carried forward
- D-P2-12 OPEN: LIST_STATE = "all" admits open PRs (125 of them). Phase 4.
- D-P2-14 OPEN: files_changed / additions / deletions fill rule. Days 11-12.
- D-P2-15 OPEN: .cache/prs/ snapshot drifts silently. Before Phase 5.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers. Before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 through the namespaced
  fetch_diff path. Three requests. Plus p5.js /labels confirmed.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens, range 64-614,
  median 387. Any anchor written against it says so.
- README at Phase 9 owes FIVE exclusion counts, not four — and must state which
  files_changed reading won (D-P2-14).
- Migration 002 for judgments.self_authored.
- 04 §5 needs a step 3b line for diff_unavailable in the doc revision pass.
- Reserved (CodeDay), Good First Issue, Help Wanted: process labels, NOT exclusions.
- fetch_diff raises httpx.HTTPStatusError on any non-406 4xx/5xx. The step-3
  caller must catch that AND DiffUnavailable — 04 §5 forbids hard-failing on one PR.
- MAX vs mean-of-top-3: Day-4 evidence exists (0.6788 -> 0.7074). Milestone A.
- Six doc revisions for the Cloud Run pivot: 04, 05, 08.

## Decisions log watermark
- Current through D-P2-15. RESOLVED today: D-P2-4, D-P2-5. OPEN: D-P2-12,
  D-P2-14, D-P2-15, D-P3-1, D-P3-2, D-P5-2.

## Schedule
- Day 10 of 50. 09 §3 puts diff_parser.py at 11-12 and index_repo wiring at 13.
- Phase 2's deliverable is a populated pull_requests table. Still EMPTY.
  Steps 1 and 2 are done and verified; steps 3-7 are not started.