# Handoff — 2026-08-08, Day 15 (Area:* stratification killed on evidence; no diffs fetched)

## Done and committed
- scripts/label_histogram.py — Area:* histogram over the frozen 44-page
  cache, zero API calls. Reuses from_list_item + apply_corpus_filter and
  joins labels off the raw items on `number`; PRMeta has no labels field
  and was deliberately not widened. Imports PR_LIST_CACHE from
  ingest/constants.py rather than redefining a cache path.
- DECISIONS.md: D-P2-21 narrowed, D-P2-22 opened. JOURNAL.md: 2026-08-08.
- Golden assertion line 3 CLOSED — pattern grepped from test_chunking.py:14,
  not retyped. That open loop is done.
- 3 commits that were ahead of origin: pushed.

## Measured — read these before deciding anything
- 44 pages, 4372 raw items, no duplicate numbers. in_corpus = 3685, matches
  the published count. The join is sound.
- 11 distinct Area:* labels. 215/3685 = 5.8% carry any. Mean 1.05 per
  labelled PR.
- Area:WebGL 121 (2017-07..2023-12) is the largest by 4x. Area:Color is 3.
- Scheme is retired: Events ends 2019-06, IO 2019-07, Utilities 2019-09,
  WebGL 2023-12. Only Typography reaches 2026, at 12 PRs over 11 years.
- Non-Area labels for context: Documentation 132, Unit Testing 32,
  Translation 29, Friendly Errors 23, p5.js 2.0+ 20, p5.strands 1.

## Prediction gaps
- distinct labels 15-30 -> 11. fraction <15% -> 5.8% (bracket correct).
  top area colour/image -> Area:WebGL (wrong, answered from the recent end).
- Union ~215 landed by two cancelling errors. See JOURNAL. Do not treat it
  as a validated model.

## NEXT SESSION STARTS HERE
1. `git status` and `pytest tests/unit -q` — expect clean, 28 passed.
2. THE 50-DIFF TIMING RUN. This is what D-P2-21 is gated on. Register
   predicted seconds-per-diff in JOURNAL BEFORE running. Fetch diffs for
   50 PRs, time it, extrapolate to 3685. Under ~2 hrs unattended -> no cut,
   fetch everything. Over -> cut, and the subset rule is recent-N or
   src/ path-prefix, NOT Area:* (dead per D-P2-22).
   The step-3 caller must catch httpx.HTTPStatusError AND DiffUnavailable —
   04 §5 forbids hard-failing on one PR.
3. After ~500 PRs land: chunk count + `pg_database_size`. Second D-P2-21
   gate is 02 §11's 250 MB target.
4. Phase 2 steps 3-7.

## Doc 12 ritual — chunking.py
- Ran in the originating chat, not here. If it did NOT actually run on
  Day 15, it is now past 12 §2's two-day window — flag the lag first thing.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton 433 MB.
- Neon: schema v001, 6 tables, EMPTY.
- Migration 002 (judgments.self_authored) still unwritten — before Phase 5.

## Schedule
- Day 15 of 50. Phase 2 deliverable STILL unmet: pull_requests EMPTY,
  steps 3-7 not started. Phase 3 (days 15-20) starts today on paper.
- Day 16 assumes chunks in Postgres. That will not hold.
- Day 20 marker: vector-only retrieval returning results. Five days out.
- Day 24 hard deadline: temporal filter test. Cannot slip (09 §5).

## Open loops
- Path import in label_histogram.py may now be unused — ruff check.
- test_chunking.py's translations test calls is_excluded() directly rather
  than parsing a diff fixture. Weaker than 07 §4 intends. Hand-build a
  p5.js fixture when convenient.
- ruff does NOT cover tests/ unless named. Use
  `ruff format app/ ingest/ scripts/ tests/ && ruff check app/ ingest/ scripts/ tests/`.
- zsh: inline `#` unsafe without interactive_comments; glob-bearing flags
  like `--include=*.py` must be quoted.
- 04 §5 documents `python scripts/index_repo.py --repo <slug>`. Positional
  now, and --refresh exists. Doc revision.
- 09 §3's day-11-12 row names ingest/diff_parser.py. Stale per D-P2-17.
- 07 §4's duplicate-triple bullet is factually wrong. D-P2-18.
- 07 §4's was_truncated bullet belongs under Embedding. D-P2-19.
- 01 §2 needs an amendment sentence for D-P2-16.
- 02 §4 needs the D-P2-14 divergence sentence.
- 04 §5 needs a step 3b line for diff_unavailable.
- a7b4835 reuses e94e9ba's subject verbatim.
- README owes: 5 exclusion counts (POST-guard), ratio-branch precision 3/10,
  the D-P2-16 delta (9 groups, 18 PRs), the D-P2-14 divergence, and now the
  Area:* coverage figure if stratification is mentioned anywhere.

## Open decisions
- D-P2-12 OPEN: LIST_STATE = "all" admits open PRs (126). Phase 4.
- D-P2-18 OPEN: 07 §4's triple invariant is wrong. Doc-revision batch.
- D-P2-20 OPEN: .yml/.yaml/.json absent from 03 §2's exclusion list.
  Resolve with the extension-distribution query after step 4.
- D-P2-21 OPEN (narrowed): no cut by default, gated on the 50-diff timing
  run and the 250 MB check. Distinct exclusion_reason clause holds either way.
- D-P2-22 OPEN: 01 §8's Area:* claim is false; scheme retired ~2023.
  Doc-revision batch. Also blocks eval_queries.subsystem — see D-P5-2.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems STALE — and §8 is now known
  wrong, not just stale (D-P2-22). Day 25.
- D-P5-3 OPEN: dual-branch ports inflate Recall@3. 8497/8498. Before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 via fetch_diff.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens.
- Migration 002 for judgments.self_authored.
- MAX vs mean-of-top-3: Day-4 evidence exists (0.6788 -> 0.7074). Milestone A.
- Six doc revisions for the Cloud Run pivot: 04, 05, 08.

## Decisions log watermark
- Current through D-P2-22.

- chunking.py was committed with a live B905 (bare zip). Fixed Day 15 with
  strict=True. `ruff check` did not run before that commit — the gap was
  the check not running at all, not running narrow.