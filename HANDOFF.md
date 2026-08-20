# Handoff — 2026-08-17, Day 21 (09 Day 17 COMPLETE — vector query + D-P2-24 closed)

## Done and committed
- app/retrieval/signals.py: VECTOR_SIGNAL_SQL + vector_signal(). Takes an
  open asyncpg.Connection rather than acquiring one — keeps app/ off both
  ingest/ (06 §10) and eval/ (invariant 12) with three callers ahead.
  Alias is vector_score_raw (invariant 6). No ::vector cast (D-P3-1).
  Guards: (384,) shape, tz-aware created_at. The tz guard is the one that
  matters — a naive datetime shifts invariant 1's boundary by the local
  offset with nothing raised.
- app/retrieval/constants.py: VECTOR_TOP_K = 50. Embedding constants grouped
  (handoff open loop closed).
- spikes/day17_vector_query.py: read-only. `local|neon` + optional `mid`.
- D-P2-24 CLOSED. 48.3 ms newest / 29.8 ms mid-history, local.
- Tests: 35 passing (no new tests — spike, not module).

## NEXT SESSION STARTS HERE
1. `git status` clean, `pytest tests/unit -q` = 35, `docker compose up -d`.
   `set -a && source .env && set +a && echo ${#DATABASE_URL_DIRECT}` → 140.
2. **FIRST DECISION, BEFORE ANY CODE — the Phase 4 cut.** Deferred twice
   under the fatigue guard. Do not start Phase 4 work until it is written.
   Standing proposal: drop Day 23's naive weighted sum. 01 §9 needs four
   pool variants; vector-only / BM25-only / file-only are three, and a crude
   untuned hybrid adds little pool diversity. Counter-argument to weigh:
   the union candidate set (03 §4) is NOT the cuttable part — it is the
   thing every later normalization depends on.
3. **09 Day 18 — chunk→PR aggregation across query chunks.**
   - SQL MAX aggregates over CANDIDATE chunks. Day 18 aggregates the 13.1
     per-chunk result lists into one PR-level ranking. 03 §5.
   - MAX default, mean-of-top-3 behind a flag. Both compared at Day 34 —
     do not pick a winner now.
   - Concrete MAX weakness already observed: on query #9032, PR #4132
     "Test pr" (2019, throwaway) scored 0.70 and outranked three real
     workflow PRs. Use it in the Phase 6 write-up.
   - Milestone A is met only after this lands. Tag v0.1-vector-only then.
4. Run the spike against `neon`. Every number so far is Docker/macOS.

## Measured — Day 17
- Local, EXPLAIN ANALYZE: newest PR 48.3 ms (3,195 candidates / 41,885
  joined rows), mid-history 29.8 ms (1,600 / 22,903). Seq Scan ~10 ms both.
- Per-chunk wall clock: first 199 ms, median 26.8 ms. First-call overhead is
  prepare + codec, not network — localhost RTT ~2 ms.
- 11 chunks = 527 ms. At 13.1 mean chunks, worst case ~630 ms server-side,
  excluding request-time embedding on Cloud Run x86.
- Temporal filter with teeth: Rows Removed by Filter 1,596 of 3,196.

## Open loops
- **Ties in the ranking (D-P6-1).** Three PRs at +0.7237, two at +0.6568.
  Duplicate chunk content. Affects Recall@3 and MRR ordering.
- Spike prints the LAST chunk's ranking, not an aggregate. Day 18 fixes.
- `ON CONFLICT DO NOTHING` verification still unrun.
- 09 Day 15 `docker stats` container memory still owed. 512 MiB vs 1 GiB.
- Cloud Run is CPU-only x86. Never carry 39 chunks/s (MPS) or 5/s (Neon).
- test_embedding.py in tests/unit costs ~10 s. Move or accept.
- index_repo.py prints `no_source_content 470 predicted 220` every run.
- Local DB 147 MB vs Neon 133 MB — dead tuples. VACUUM FULL. Cite Neon.
- README owes: no_source_content 470 (12.8%), truncation 23.3% (02 §5).
- Fixture misses .map/.obj/.mtl/.stl exclusions (30 appearances).
- `build_all_rows` reaches `gh._diff_cache_path`. Private-attribute debt.
- 12 Day-4 spike diffs still use the unreachable naming scheme.
- Spike invocation is `python -m spikes.x`, not `python spikes/x.py` —
  check day3/day4 for a second convention before it sets.
- zsh: bare SQL is not a command. Always `psql "$URL" -c "..."`.
  Adjacent string literals concatenate with NO space.

## Doc 12
- chunking.py COMPLETE (Day 14). No lag.
- signals.py has 1 of 3 signals. Ritual is owed at Phase 4 close, not now.
- Remaining: normalize.py, signals.py, scoring.py, reasons.py, eval/pool.py,
  eval/score.py.

## Schedule
- Day 21 of 50. Phase 3 Day 18 remains. Phase 4 (21-24) has not started.
- **Day 24 HARD deadline: temporal filter test (07 §9).** Binding constraint
  is ORDER — it lands before Phase 5 pooling. A leak found after labeling
  means relabeling ~300 judgments. Day 17's spike assertion is a smoke test,
  not that test.
- Milestone A (vector-only retrieval returning results) NOT yet met.

## Open decisions
- **PHASE 4 CUT — decide at open.** See step 2.
- D-P6-1 OPEN: ranking ties. Before Day 34.
- D-P2-12 OPEN: LIST_STATE="all" admits 126 open PRs. Phase 4.
- D-P2-18, D-P2-22 OPEN: doc-revision batch. Now includes 02 §5's no-ANN
  rationale and 03 §5's alias + redundant cast.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors / §8 subsystems. Day 25.
- D-P5-3 OPEN: 8497/8498 both confirmed in corpus. Before Day 25.

## Decisions log watermark
- Current through D-P6-1. D-P2-24 closed this session.