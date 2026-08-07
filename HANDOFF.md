# Handoff — 2026-08-06, Day 13 (D-P2-15 closed; D-P2-16 implemented; 51/3,685 locked)

## Done and committed
- ingest/github_client.py: requests_made counter, per round trip incl. retries.
- scripts/index_repo.py: argparse replaces sys.argv[1]. --refresh now parses
  and threads to GitHubClient; unknown flags rejected. requests printed;
  frozen branch asserts requests_made == 0. Seven message defects fixed in
  assert_list_is_sound (set literal, five dropped spaces, FastAPI's 4,900 —
  the band now interpolates EXPECTED_TOTAL_*).
- ingest/corpus_filter.py: discard_multi_merged_groups(), named function
  between group_duplicates() and pick_keeper(). Called at the step-2 site.
- tests/unit/test_corpus_filter.py: two tests, both watched failing.
- DECISIONS.md: D-P2-15 amended, D-P2-16 RESOLVED+IMPLEMENTED, D-P2-17 and
  D-P2-18 added. JOURNAL.md: 2026-08-06.

## Measured — D-P2-16 met its prediction on all three figures
- Registered 47 / 51 / 3,685. Measured 47 / 51 / 3,685.
- 56/60/3,676 are PRE-GUARD and superseded everywhere they appear.
- Nine groups discarded, 18 PRs returned to corpus.
- 8497/8498 never formed a group — " (main)" suffix defeats exact match.
  Real dual-branch port, both merged, both in corpus. First named instance
  of D-P5-3. D-P2-16 catches grouped ports only.

## D-P2-15 CLOSED
- Four teeth watched failing, four sites: 224 wrong total / 211 missing page
  / 218 stray page / 246 --refresh.
- Check 4 initially did NOT fire: --refresh was honoured at three sites in
  github_client but index_repo never supplied it. Reference-location class.
- Frozen run prints `requests 0` and asserts it. Direct observation replaces
  the elapsed-0s inference. The "zero HTTP lines in the log" criterion was
  never runnable — basicConfig has no FileHandler.
- PROCEDURE, not enforceable in code: --thaw then freeze re-derives the
  manifest FROM THE CACHE, so it always resolves disagreement in the cache's
  favour. Thaw, READ the printed totals, then freeze. Never chain.
- Manifest re-derived today: frozen_at now 2026-08-06T07:17:49Z. Contents
  identical (44 pages / 4,372 / #16 / #9032).

## NEXT SESSION STARTS HERE
1. `git status` and `pytest tests/unit -q` — expect clean, 14 passed.
2. D-P2-14 — files_changed / additions / deletions fill rule. Untouched for
   four sessions. Recommendation on record: files_changed = files surviving
   03 §2; additions/deletions = every file, matching GitHub. DECIDE it, but
   note it cannot be IMPLEMENTED until step 4 parses a diff.
3. app/retrieval/chunking.py — start it. This is the real schedule debt.
   Per D-P2-17 it is NOT ingest/diff_parser.py; delete that empty file.
   Doc 12 ritual fires when its golden assertion passes.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton 433 MB.
- Neon: schema v001, 6 tables, EMPTY.
- Migration 002 (judgments.self_authored) still unwritten — before Phase 5.

## Open loops
- Day-11 teeth check still half-run: the two in_corpus assertions in
  test_high_ratio_titles_do_not_group were never watched failing.
- ruff check does NOT cover tests/ unless named. Use
  `ruff format ingest/ scripts/ tests/ && ruff check ingest/ scripts/ tests/`.
- 04 §5 documents `python scripts/index_repo.py --repo <slug>`. Positional
  now, and --refresh exists. Doc revision.
- 09 §3's day-11-12 row names ingest/diff_parser.py. Stale per D-P2-17.
- 07 §4's duplicate-triple bullet is factually wrong. D-P2-18.
- 01 §2 needs an amendment sentence for D-P2-16.
- a7b4835 reuses e94e9ba's subject verbatim. Ledger-only commits need their
  own subject line.
- README owes: 5 exclusion counts (POST-guard), ratio-branch precision 3/10,
  and the D-P2-16 delta (9 groups, 18 PRs returned).

## Open decisions
- D-P2-12 OPEN: LIST_STATE = "all" admits open PRs (126). Phase 4.
- D-P2-14 OPEN: files_changed / additions / deletions fill rule. Next session.
- D-P2-18 OPEN: 07 §4's triple invariant is wrong. Doc-revision batch.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers. Day 25.
- D-P5-3 OPEN: dual-branch ports inflate Recall@3. 8497/8498 is the first
  named instance. Before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 via fetch_diff.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens.
- Migration 002 for judgments.self_authored.
- 04 §5 needs a step 3b line for diff_unavailable.
- fetch_diff raises httpx.HTTPStatusError on any non-406 4xx/5xx. The step-3
  caller must catch that AND DiffUnavailable — 04 §5 forbids hard-failing.
- MAX vs mean-of-top-3: Day-4 evidence exists (0.6788 -> 0.7074). Milestone A.
- Six doc revisions for the Cloud Run pivot: 04, 05, 08.

## Decisions log watermark
- Current through D-P2-18.

## Schedule
- Day 13 of 50. 09 §3 puts chunking at 11-12 and index_repo wiring at 13.
  Chunking not started. ~2.5 days behind and the gap is widening.
- Phase 2's deliverable is a populated pull_requests table. Still EMPTY.
  Steps 1-2 done and now stable; 3-7 not started.
- Step 2 is finished. Every remaining step-2 item is a doc revision, not code.
  The next session should open on chunking, not on the filter.