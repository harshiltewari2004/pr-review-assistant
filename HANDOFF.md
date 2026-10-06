# Handoff — Day 30 close

## State
- HEAD: <fill in after commit> on `main`, pushed, clean tree
- Tests: 88 passed, 1 skipped
- #8994 baseline (default weights): #8259 0.9255, #6222 0.8914, #8821 0.8850, |C|=143
- eval/pool.json: 345 candidates, 20 queries, byte-identical across runs
- Target: Day 57 (D-M-2). Phase 5: Days 28–34.

## Gate
```bash
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check .
pytest -q
python -m scripts.day27_orchestrator_spike
cp eval/pool.json /tmp/pool_before.json
python -m eval.pool > /dev/null
cmp eval/pool.json /tmp/pool_before.json && echo "BYTE-IDENTICAL"
```
Read each output before the next command.

## Shipped Day 30
- Censoring check: 0/20 queries, 0/120 PRs → vector-only ranks within C
- eval/pool.py (D-P5-8): 5 variants, raw > 0 evidence rule, temporal assert
- Doc 12 ritual on pool.py done; 7 pool tests, teeth-checked

## 🎯 NEXT SESSION — fixed order
1. Move pool.json to eval/artifacts/ (04 §3): git mv + POOL_PATH, re-run,
   must stay byte-identical.
2. eval/label.py — blind labeling CLI (plumbing, paste). 01 §10: shuffle
   pool, strip rank/variant, grade + reason (≤6 words, required for 1–2)
   + seconds, skip ≤5%, round = 1, never overwrite round 1.
3. Batch 1: 10 queries (~170 judgments), one sitting.

## Open
- D-P5-9 W2: pool.json records no inputs (git HEAD, snapshot). Fix before
  eval/score.py reads it.
- D-P5-9 W3: Phase 6 must report unjudged rate of tuned top-3 (must be 0).

## Owed
- Typo batch: scoring.py docstrings, test_scoring.py docstring
- 03 §9 / invariant 5 wording: non-negative weights
- Vector nomination 596 ms — per-chunk-scan hypothesis (Phase 7)
- normalize.py docstring: degenerate-0.0 reason is 03 §10 thresholds
- 03 §8: BM25 "0 to 15+" stale (measured 52–298)
- 01 §8: replace FastAPI-era subsystem list with D-P5-5 path strata
- 01 §9: note pool came out 345, not ~300
- 10 §7: add "Recall@3 is pool-relative" answer
- #6922: in_corpus open item
- README limitations: label coverage, docs-only queries excluded, #5460,
  pool-relative recall
- (all prior items still owed)