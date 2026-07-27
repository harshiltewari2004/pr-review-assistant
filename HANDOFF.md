# Handoff — 2026-07-26, end of Phase 1 Day 3 (pgvector spike)

## Done and committed
- spikes/day3_pgvector.py — asyncpg round-trip through the real chunks
  table inside a rolled-back transaction. Ran against 4 targets: local
  docker, Neon direct, Neon pooled (default cache), Neon pooled
  (statement_cache_size=0). All 4 PASS.
- Verified on all targets: 6 tables, chunks.embedding = vector(384),
  cosine {identical +1.0, 2a +1.0, orthogonal 0.0, opposite -1.0},
  float4 round-trip delta 9.359e-09, wrong-dimension rejected (DataError),
  0 rows left behind after rollback.
- Fixed HANDOFF filename casing (was HANDOFF.MD, untracked since day 2).

## Deployed state
- Service: not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton builds
  locally, 433 MB.
- Neon: schema v001, 6 tables, empty — no corpus indexed yet. pgvector
  0.8.0. Local docker: pgvector 0.8.5 (see D-P1-3).

## Open decisions carried forward
- D-P2-2 OPEN: production github_client.py handling of 406 on large diffs —
  /pulls/{n}/files fallback vs log-and-skip.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec in app/db.py.
  Decide with a measurement at Phase 3 bulk insert.
- D-P3-2 OPEN: Neon pooled + asyncpg pool untested. Single connection
  passed; create_pool() under Cloud Run churn is the real test, Phase 7.
  statement_cache_size=0 is the known fallback.

## Carried-over obligations
- Phase 2 github_client.py inherits the spike's rate-limit/backoff pattern
  and the 406 decision.
- huge_hunk.diff is a char-heuristic candidate — confirm it actually trips
  was_truncated with MiniLM's tokenizer in Phase 3.
- Doc revision batch (now 7 items): six from the Cloud Run pivot across
  04/05/08, plus 03 §3's claim that normalize_embeddings=True is what makes
  <=> behave as cosine. Measured false — <=> is magnitude-invariant. Keep
  the flag, fix the stated reason. Do these in one pass, not piecemeal.

## Decisions log watermark
- Current through D-P3-2, committed. Numbering convention now documented
  at the top of DECISIONS.md.

## Next session starts with
- Day 4: embedding sanity spike, BOTH repos (08 §8, 09 §5). Two
  known-similar PR pairs from fastapi/fastapi and two from processing/p5.js.
  Pick pairs whose similarity is IN THE CODE, not the title. Resolves
  D-P1-2 (primary evaluation repo). This is the only assumption that could
  reshape the project — hard deadline, cannot slip.