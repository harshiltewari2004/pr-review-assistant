# Handoff — 2026-08-07, Day 14 (chunking.py landed; Phase 2 deliverable still unmet)

## Done and committed
- app/retrieval/chunking.py: parse_hunks() (pure str -> list[Hunk]),
  is_excluded(), files_changed(), diff_totals(), _render(), _new_path().
  Line-anchored ^@@ regex; path searched only in block[:first_hunk] so a
  content line rendering as "+++ " cannot hijack the path.
- tests/unit/test_chunking.py: 14 tests. 28 passing total.
- ingest/diff_parser.py deleted (D-P2-17).
- tests/fixtures/diffs/multi_file.diff -> md_excluded.diff (misnamed).
- DECISIONS.md: D-P2-14 RESOLVED, D-P2-19 RESOLVED, D-P2-20 OPEN,
  D-P2-4 teeth addendum. JOURNAL.md: 2026-08-07.

## Measured — all seven fixture predictions met
- simple_single_file 1 / at_marker 1 / md_excluded 1 / deleted_file 0 /
  rename_only 0 / binary_file 2 / huge_hunk 23. Registered before the run.
- huge_hunk: +447/-167 across 5 .py files, hunk_index per-file
  [0,1,2] / 0-10 / [0,1] / 0-5 / [0]. Reset across the boundary observed
  directly (models.py 2 -> utils.py 0).
- Trailing context retained, no header digits, verified by reading content
  not by the assertion alone.

## Golden assertion — PASSES, teeth partly watched
- test_golden_simple_single_file, 3 lines per 07 §3.
- Lines 1 and 2 watched failing. Line 3's teeth check was INVALID: inverting
  the regex assertion proves nothing about whether the pattern is dead.
  DO THIS FIRST NEXT SESSION if not done today:
    python -c "import re; print(re.compile(r'-\d+(?:,\d+)? \+\d+(?:,\d+)? @@').search('@@ -120,7 +120,9 @@ def f('))"
  Must print a match object.

## Doc 12 ritual — DUE
- chunking.py is one of the seven modules and its golden assertion passes.
  Ritual applies as of Day 14. 12 §2 gives a two-day window before the
  reasoning goes cold. If not run by Day 16, flag the lag at session open.
- Three lines flagged for step 6 (non-obvious lines):
  block[:first.start()] path scoping; the shape-constrained ^@@ regex;
  _render dropping the literal @@ marker.

## NEXT SESSION STARTS HERE
1. `git status` and `pytest tests/unit -q` — expect clean, 28 passed.
2. THE CORPUS-SIZE DECISION, before any diff fetching. 09 §6's Day-14 risk
   marker fired: prescribed response is 500 PRs instead of full history.
   Proposed modification: keep the frozen 4,372 list and the 3,685
   in_corpus marks (cheap, already fetched, README counts already published);
   cut at STEP 3 — fetch and chunk diffs for a bounded subset only.
   Open question: recent-N vs stratified across Area:* labels. 01 §8 needs
   >=6 subsystems across 20 queries, so stratified is probably right.
   Log as D-P2-21. This determines what gets fetched — decide first.
3. Phase 2 steps 3-7. Step 3 (fetch_diff over the chosen subset) is the
   critical path.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton 433 MB.
- Neon: schema v001, 6 tables, EMPTY.
- Migration 002 (judgments.self_authored) still unwritten — before Phase 5.

## Schedule
- Day 14 of 50. Phase 2 (days 8-14) ENDS TODAY with its deliverable unmet:
  pull_requests EMPTY, steps 3-7 not started.
- 09 §6's Day-14 risk marker has fired. See item 2 above.
- Phase 3 (days 15-20) starts tomorrow; day 16 assumes chunks in Postgres.
- Day 20 marker: vector-only retrieval returning results. Six days out,
  no buffer left.

## Open loops
- Line 3 of the golden assertion — regex liveness unproven (see above).
- test_chunking.py's translations test calls is_excluded() directly rather
  than parsing a diff fixture. Weaker than 07 §4 intends. No p5.js fixture
  exists for it; hand-build when convenient.
- ruff check does NOT cover tests/ unless named. Use
  `ruff format app/ ingest/ scripts/ tests/ && ruff check app/ ingest/ scripts/ tests/`.
- zsh: inline `#` comments unsafe without interactive_comments.
- 04 §5 documents `python scripts/index_repo.py --repo <slug>`. Positional
  now, and --refresh exists. Doc revision.
- 09 §3's day-11-12 row names ingest/diff_parser.py. Stale per D-P2-17.
- 07 §4's duplicate-triple bullet is factually wrong. D-P2-18.
- 07 §4's was_truncated bullet sits under Chunking; belongs to Embedding.
  D-P2-19.
- 01 §2 needs an amendment sentence for D-P2-16.
- 02 §4 needs the D-P2-14 divergence sentence: source-only totals will not
  match GitHub's PR page.
- 04 §5 needs a step 3b line for diff_unavailable.
- a7b4835 reuses e94e9ba's subject verbatim.
- README owes: 5 exclusion counts (POST-guard), ratio-branch precision 3/10,
  the D-P2-16 delta (9 groups, 18 PRs returned), and the D-P2-14 divergence.

## Open decisions
- D-P2-12 OPEN: LIST_STATE = "all" admits open PRs (126). Phase 4.
- D-P2-18 OPEN: 07 §4's triple invariant is wrong. Doc-revision batch.
- D-P2-20 OPEN: .yml/.yaml/.json absent from 03 §2's exclusion list.
  Resolve with the extension-distribution query after step 4.
- D-P2-21 (to open): corpus-size cut. Next session, item 2.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers. Day 25.
- D-P5-3 OPEN: dual-branch ports inflate Recall@3. 8497/8498. Before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 via fetch_diff.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens.
- Migration 002 for judgments.self_authored.
- fetch_diff raises httpx.HTTPStatusError on any non-406 4xx/5xx. The step-3
  caller must catch that AND DiffUnavailable — 04 §5 forbids hard-failing.
- MAX vs mean-of-top-3: Day-4 evidence exists (0.6788 -> 0.7074). Milestone A.
- Six doc revisions for the Cloud Run pivot: 04, 05, 08.

## Decisions log watermark
- Current through D-P2-20.