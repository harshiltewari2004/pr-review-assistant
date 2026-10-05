# Handoff — Day 28 close

## State
- HEAD: <ledger commit hash> on `main`, pushed, clean tree
- Tests: 72 passed, 1 skipped (no app/ changes today)
- eval_queries: 20 rows, 7 strata, 10 tune / 10 holdout (2fc72cc)
- Target: Day 57 (D-M-2). Phase 5: Days 28–34.

## Gate
```bash
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
ruff check && ruff format --check .
pytest -q
python -m eval.select_queries   # must reproduce the same 20 (dry run)
```

## 🎯 NEXT SESSION — fixed order
1. Decide D-P4-14: rank_candidates gets a `weights` parameter (default =
   constants) and returns per-signal norms, plus the key-set assert.
   Blocks pool.py.
2. eval/pool.py — typed, piece by piece. 01 §9: 4 variants (vector,
   BM25, file, hybrid × 2 weight settings), top-6 each, temporal
   filter, union, ~15 per query.
3. Doc 12 ritual on pool.py when its golden assertion passes.

## Owed (additions today)
- Per-stage timing in find_similar_prs (860 ms total, only backfill timed)
- normalize.py docstring: the degenerate-0.0 reason is the 03 §10 thresholds
- 03 §8: BM25 "0 to 15+" is stale (measured 52–298)
- 01 §8: replace the FastAPI-era subsystem list with the D-P5-5 path strata
- #6922: in_corpus open item (DECISIONS L1372)
- README limitations: label coverage, docs-only queries excluded, #5460
- (all prior items still owed)