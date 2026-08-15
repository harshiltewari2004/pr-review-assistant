# Handoff — 2026-08-15, Day 21 (04 §5 steps 5-6 COMPLETE — chunks written)

## Done and committed
- **41,899 chunks with 384-dim vectors on BOTH local and Neon.** 3,196 PRs,
  23.3% truncated (9,748). Two independent runs, identical counts — the
  pipeline is deterministic from the frozen cache.
- ingest/chunk_rows.py: `ChunkRow`, `build_chunk_rows`, `as_params()`.
  `was_truncated = token_count > MAX_MODEL_TOKENS` (invariant 9). `zip(...,
  strict=True)` guards hunk/count/vector alignment — misalignment would
  produce valid-looking rows with wrong vectors.
- ingest/db.py: `register_vector(conn)` (D-P3-1), `INSERT_CHUNK` with
  ON CONFLICT DO NOTHING, `SELECT_CHUNKED_PR_IDS`.
- scripts/index_repo.py: `store_chunks` (steps 5-6), `--limit`,
  `--chunks-only`. Commits PER PR, not one transaction — see below.
- scripts/chunk_projection.py DELETED. Projected 8 chunks/PR against a
  measured 13.1.
- requirements.txt: pgvector pinned.
- Tests: 35 passing.

## NEXT SESSION STARTS HERE
1. `git status` clean, `pytest tests/unit -q` = 35, `docker compose up -d`.
   `set -a && source .env && set +a && echo ${#DATABASE_URL_DIRECT}` → 140.
2. Verify both DBs:
   `psql "$DATABASE_URL_LOCAL"` and `psql "$DATABASE_URL_DIRECT"` →
   `SELECT count(*), count(embedding), count(DISTINCT pr_id) FROM chunks;`
   Expect 41899 / 41899 / 3196 on both.
   **`$DATABASE_URL` is Neon pooled — `$DATABASE_URL_LOCAL` is Docker.**
3. **09 Day 17 — vector similarity query.** Top 10 by cosine `<=>`,
   temporal filter enforced in SQL.
   - **Invariant 1: `candidate.created_at < query.created_at`.** First code
     where a bug invalidates published numbers instead of costing a re-run.
   - Filter `in_corpus` AND `repo_id` before the vector scan.
   - Exclude the query PR's own chunks.
   - pgvector's read path returns a `Vector`, NOT an ndarray — `.to_numpy()`
     before anything numpy touches it (D-P3-1 consequence).
   - Name it `vector_score_raw` (invariant 6). Cosine *distance* is
     `<=>`; similarity is `1 - (a <=> b)`.
   - Run `EXPLAIN ANALYZE` and record actual latency at 41,899 chunks —
     that closes D-P2-24.

## Why store_chunks commits per PR
`write_rows` is one transaction because a half-written `pull_requests` makes
the reconciliation counts describe a corpus that does not exist. `store_chunks`
is the opposite: embedding is the expensive step, so one transaction around
3,196 PRs means an interruption rolls back everything and the resume query
finds nothing. Atomicity there would make the run un-resumable.

The unit of atomicity matches the unit of resumption — any chunk that exists
is complete, any incomplete PR is redone.

## Open loops
- **`ON CONFLICT DO NOTHING` verification** — the resume check prevents a
  conflict from ever reaching Postgres, so the normal path cannot test it.
  Verify with a self-referential `INSERT ... SELECT ... ON CONFLICT DO
  NOTHING` expecting `INSERT 0 0` if not already done.
- 09 Day 15 still owes the `docker stats` container memory reading. Host
  process was 360 MB on macOS arm64/MPS — not the governing number.
  If the container agrees, Cloud Run gets 512 MiB, not 1 GiB.
- `Use pytorch device_name: mps` — 39 chunks/s local is Apple GPU. Cloud Run
  is CPU-only x86. The query path embeds at request time on that CPU. Do not
  carry 39/s (or Neon's 5/s) into any latency estimate.
- test_embedding.py sits in tests/unit and costs ~10s. Fast loop was 0.08s.
  Decide: move to tests/integration, or accept.
- constants.py: EMBEDDING_DIM line 8, EMBEDDING_MODEL 23, EMBED_BATCH_SIZE
  27 — four constants for one model in three places. Group them.
- index_repo.py prints `no_source_content 470 predicted 220` every run.
  Permanent noise. Update to 470 or drop the line.
- Local DB is 147 MB against Neon's 133 MB for identical rows — dead tuples
  from repeated UPSERT runs. `VACUUM FULL` closes it. Cite Neon's figure.
- README owes: no_source_content 470 (12.8% of fetched), and truncation
  23.3% corpus-wide (02 §5).
- Fixture does not cover .map/.obj/.mtl/.stl exclusions (30 appearances).
- `build_all_rows` reaches `gh._diff_cache_path`. Private-attribute debt.
- 12 Day-4 spike diffs still use the unreachable naming scheme.
- zsh: inline `#` becomes a filename argument. Save files before
  `ruff format`. Adjacent string literals concatenate with NO space — the
  cause of the `pull requestsWHERE` syntax error today.

## Doc 12
- chunking.py ritual COMPLETE (Day 14). No lag.
- embedding.py, chunk_rows.py, db.py, pr_rows.py, index_repo.py are NOT on
  the seven-module list (12 §1). Normal review only.
- Remaining six: normalize.py, signals.py, scoring.py, reasons.py,
  eval/pool.py, eval/score.py. None built yet.

## Schedule
- Day 21 of 50. Phase 3 (days 15-20) overran; Phase 4's window (21-24) is
  being spent on Phase 3 work. Day 17 and 18 of Phase 3 remain.
- Day 20 Milestone A (vector-only retrieval returning results) not met.
- **Day 24 HARD deadline: temporal filter test.** 07 §9 — the binding
  constraint is ORDER, not date: it lands before Phase 5 pooling, because a
  leak found after labeling means relabeling ~300 judgments. Do not compress
  Phase 4 to recover calendar and let this slide past pooling.
- Phase 4 (three signals crude) has not started.

## Open decisions
- D-P2-12 OPEN: LIST_STATE="all" admits 126 open PRs. Phase 4.
- D-P2-18, D-P2-22 OPEN: doc-revision batch. Now includes 02 §9 storage
  (133 MB not ~50 MB), 02 §5 chunk count (41,899 not ~10,000), 02 §5
  truncation (23.3%), and 03 §3's wrong `normalize_embeddings` rationale.
- D-P2-24 UPDATED, still OPEN: 4.2× off, not ~2.5×. Closes at Day 17 with
  EXPLAIN ANALYZE. Criterion is latency, not chunk count.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors / §8 subsystems. Day 25.
- D-P5-3 OPEN: 8497/8498 both confirmed in corpus. Before Day 25.

## Decisions log watermark
- Current through D-P3-3. D-P3-1 resolved this session.