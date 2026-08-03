# Handoff — 2026-08-03, Day 11 (D-P2-4 landed and validated; cache still drifting)

## Done and committed
- ingest/corpus_filter.py: titles_match() is `normalize_title(a) == normalize_title(b)`.
  SequenceMatcher branch and difflib import deleted, not commented out.
  Docstring carries the reversal and the four PR numbers.
- ingest/constants.py: TITLE_SIMILARITY_THRESHOLD deleted, replaced by a comment
  stating why no threshold exists. Greps clean (only prose hits remain, by design).
- scripts/index_repo.py: step-2 diagnostics now print BEFORE assert_filter_is_sound,
  matching step 1's order. A failing filter assertion is now debuggable.
- tests/unit/test_corpus_filter.py: test_high_ratio_titles_do_not_group added.
  Pair scores 0.9688 — over the deleted threshold. 12 tests passing.
- Teeth check run: watched `assert not titles_match(...)` fail with the branch
  restored. NOT watched: the two in_corpus assertions (assert short-circuits).

## Measured — the prediction held
- 4,372 PRs (was 4,371 yesterday, 4,370 the day before). Last #9032, 2026-08-02T20:16Z.
- Counter: {None: 3676, duplicate_resubmission: 60, bot_author: 625, housekeeping: 11}
- 56 duplicate groups (grep -c on the run log).
- PREDICTED 55 / 59 / 3,676 / 695 on 4,371. in_corpus exact; others +1.
- Explanation: the drifted PR formed a new duplicate group. bot_author and
  housekeeping unchanged, so it is neither. NOT YET CONFIRMED against the log.

## NEXT SESSION STARTS HERE
1. Confirm the drift attribution:
   `grep "duplicate group:" /tmp/day11_filter.log | grep -E "90[23][0-9]"`
   If nothing returns, three numbers moved for a reason not yet understood.
2. D-P2-15: freeze the cache. Two drifts, second one moved a measured number.
   Every README exclusion count is computed against a moving snapshot.
3. THEN D-P2-14 — files_changed / additions / deletions fill rule. Untouched today.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton 433 MB.
- Neon: schema v001, 6 tables, EMPTY. Nothing written to Postgres.
- Migration 002 (judgments.self_authored) still unwritten — before Phase 5.

## Open loops from today
- Teeth check half-run: the two in_corpus assertions in the new test were never
  watched failing. Either finish it or accept them as unverified.
- Real duplicate group `kept #8947, excluded [8945, 8946]` — 07 §4 says the
  survivor is the merged one and the fixture marks #8946 merged. Not a bug
  (pick_keeper is deterministic), but confirm on GitHub which of the three is
  merged; 07 §4 names this exact triple.

## Field audit carried forward — 02 §4
Fourteen of seventeen columns fill from a list item. THREE DO NOT:
files_changed, additions, deletions. All have DB defaults, so a bad insert
raises nothing. All three source from the parsed diff at step 4. One question,
not three: every file in the diff, or only files surviving 03 §2? D-P2-14.

## Open decisions carried forward
- D-P2-12 OPEN: LIST_STATE = "all" admits open PRs (126 now, was 125). Phase 4.
- D-P2-14 OPEN: files_changed / additions / deletions fill rule. Next session.
- D-P2-15 OPEN: cache drift. ESCALATED — moved a measured number. Next session.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers. Before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 through the namespaced
  fetch_diff path. Three requests. Plus p5.js /labels confirmed.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens, range 64-614, median 387.
- README at Phase 9 owes FIVE exclusion counts, and must state which
  files_changed reading won (D-P2-14).
- Migration 002 for judgments.self_authored.
- 04 §5 needs a step 3b line for diff_unavailable in the doc revision pass.
- Reserved (CodeDay), Good First Issue, Help Wanted: process labels, NOT exclusions.
- fetch_diff raises httpx.HTTPStatusError on any non-406 4xx/5xx. The step-3
  caller must catch that AND DiffUnavailable — 04 §5 forbids hard-failing on one PR.
- MAX vs mean-of-top-3: Day-4 evidence exists (0.6788 -> 0.7074). Milestone A.
- Six doc revisions for the Cloud Run pivot: 04, 05, 08.

## Decisions log watermark
- Current through D-P2-15. CLOSED today: D-P2-4 (with result). OPEN: D-P2-12,
  D-P2-14, D-P2-15, D-P3-1, D-P3-2, D-P5-2.

## Schedule
- Day 11 of 50. 09 §3 puts diff_parser.py at 11-12 and index_repo wiring at 13.
  diff_parser.py exists as a file but is not started. Half a day behind.
- Phase 2's deliverable is a populated pull_requests table. Still EMPTY.
  Steps 1 and 2 done and verified; steps 3-7 not started.