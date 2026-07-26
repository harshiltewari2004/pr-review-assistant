# Handoff — 2026-07-25, end of Phase 1 Day 2 (GitHub API spike + fixtures)

## Done and committed
- spikes/day2_github_api.py — throwaway API spike: pagination, rate-limit header
  handling, backoff, .diff fetch, fixture auto-classifier. Verified live on
  fastapi/fastapi (quota fell 4974→4665 across runs, no 429s).
- tests/fixtures/diffs/ — 7 parser fixtures (5 real, 2 hand-built). See D-P2-1.
- DECISIONS.md, HANDOFF.md now tracked (were untracked since day 1).
- JOURNAL.md — day-2 entry.

## Deployed state
- Service: not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton builds
  locally, 433 MB.
- Neon: schema v001, 6 tables, empty — no corpus indexed yet.

## Open decisions carried forward
- D-P2-2 OPEN: production github_client.py handling of 406 on large diffs —
  /pulls/{n}/files fallback vs log-and-skip.

## Carried-over obligations
- Phase 2 github_client.py inherits the spike's rate-limit/backoff pattern and
  the 406 decision.
- huge_hunk.diff is a char-heuristic candidate — confirm it actually trips
  was_truncated with MiniLM's tokenizer in Phase 3.

## Decisions log watermark
- Current through D-P2-2, committed.

## Next session starts with
- Day 3: pgvector spike — insert one 384-dim vector from Python via asyncpg and
  read it back by cosine, against BOTH local Postgres and Neon (08 §8). This is
  the driver-level test the day-1 SQL check did not cover.