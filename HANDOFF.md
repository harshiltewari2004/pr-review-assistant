# Handoff — 2026-08-12, Day 18 (PHASE 2 DELIVERABLE MET — pull_requests populated)

## Done and committed
- `pull_requests` populated on LOCAL: 4,372 rows, 3,196 in corpus.
  Reasons: no_source_content 470, bot_author 625, duplicate_resubmission 51,
  diff_unavailable 19, housekeeping 11. Sums to 4,372.
- `repos`: one row, id 2, status ready, total_prs 4372, indexed_prs 3196.
  (id 1 was burned by a BIGSERIAL advance on a rolled-back run. Normal.)
- ingest/pr_rows.py: `build_row`, `PRRow`, `outcome_of`, `_ts`, `_lean_raw`.
  Typed timestamps (tz-aware), D-P2-27 raw stripping.
- ingest/db.py: asyncpg single connection, `--target local|neon` required,
  no default. JSONB codec registered. UPSERT_REPO / UPSERT_PR.
- scripts/index_repo.py: steps 3b/4/4b + `assert_pull_requests_are_sound`.
- app/retrieval/chunking.py: D-P2-20 exclusions, VISUAL_SCREENSHOTS.
- Tests: 34 passing. test_pr_rows.py covers all four build_row branches.
- DECISIONS.md: D-P2-20 RESOLVED, D-P2-25/26/27 RESOLVED, D-P2-24 updated.

## NEXT SESSION STARTS HERE
1. `git status` clean, `pytest tests/unit -q` = 34, `docker compose up -d`.
2. **Neon has NOT been written.** `python -m scripts.index_repo --target neon`,
   then verify 4372/3196 and the identical six-row reason breakdown.
   08 §5: local and Neon must not diverge. This is the one open Phase 2 task.
3. Then Phase 3: MiniLM tokenizer, `token_count`, `chunks` table (D-P2-26).

## Open loops
- Neon write unverified. 14.8 MB `raw` is the largest payload sent to Neon so
  far; transaction is atomic, so a failure leaves the table empty not partial.
- D-P3-1 still open before the chunks write: manual `::vector` cast vs pgvector
  asyncpg codec. Same class as D-P2-27's JSONB codec — resolve the same way.
- `build_all_rows` takes `diff_path`, resolved from the private
  `gh._diff_cache_path` inside the client's `with` block. Private-attribute
  reach, consistent with chunk_projection.py. Small debt.
- 470 no_source_content rows carry `files_changed = '{}'`; the `idx_pr_files`
  GIN index only ever serves in-corpus rows. Expected, not a defect.
- Chunk projection needs recomputing at 3,196 (~25,500, was 29,406).
- README owes a fourth exclusion line: no_source_content 470 (12.8% of fetched).
- Fixture does not cover `.map`/`.obj`/`.mtl`/`.stl` exclusions (30 appearances).
- 12 Day-4 spike diffs still use the unreachable naming scheme.
- zsh: inline `#` unsafe; quote glob-bearing flags.
- Save files before running `ruff format` — save conflicts otherwise.

## Doc 12
- chunking.py ritual COMPLETE (Day 14). No lag.
- Remaining six: normalize.py, signals.py, scoring.py, reasons.py,
  eval/pool.py, eval/score.py. None built yet.
- pr_rows.py, db.py, index_repo.py are NOT on the seven-module list (12 §1).

## Schedule
- Day 18 of 50. Phase 2 complete pending the Neon write.
- Phase 3 (days 15-20) starts ~3 days late. Day 20 marker — vector-only
  retrieval returning results — is 2 days out and will slip.
- Day 24 HARD deadline: temporal filter test. Cannot slip (09 §5).

## Open decisions
- D-P2-12 OPEN: LIST_STATE="all" admits 126 open PRs. Phase 4.
- D-P2-18, D-P2-22 OPEN: doc-revision batch.
- D-P2-24 OPEN: invariant 11 premise ~2.5x low at 3,196.
- D-P3-1 OPEN: ::vector cast vs pgvector codec. Phase 3, next session.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors / §8 subsystems. Day 25.
- D-P5-3 OPEN: 8497/8498 both confirmed in corpus. Before Day 25.

## Decisions log watermark
- Current through D-P2-27.