# Handoff — Day 35 close

## State
- main, pushed, clean tree. Tests: 108 passed, 1 skipped. Ruff clean.
- Phase 6 DONE, tagged v0.2-hybrid. Weights LOCKED 0.6/0.3/0.1, max (D-P6-2).
- HOLDOUT SCORED ONCE (D-P6-4): lenient R@3 0.321 [0.237, 0.421], ceiling
  0.501 (64% of achievable); strict 0.542; MRR@3 0.883 (top result relevant
  8/10). Baselines: prior 0.36, bm25 0.35, vector 0.27, file 0.16 (flagged).
  Tuning overfit; nothing re-tuned (invariant 14). holdout_scored.json committed.
- v1.1 scheduled before Phase 9 with a pre-committed headline rule (D-P6-5).

## Gate
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check . && pytest -q
python -m eval.snapshot
git status --porcelain
git tag --list 'v0.*'

## NEXT SESSION: reasons.py (TYPED, piece by piece)
1. Resolve D-P4-11 first: REASON_HIGH_* thresholds must name their scale
   (normalized per-query vs raw). Read 03 §10 and constants.py.
2. reasons.py: template reason strings from ScoredCandidate norms (03 §10),
   never LLM-generated (invariant 18), "closed without merging" wording
   (invariant 17).
3. Unit tests + teeth checks; fill the 07 §6 skipped structural test if ready.

## Open
- D-P4-11 (blocks reasons.py)
- Pooling bias (README limitation)

## Owed
- 01 §11: headline -> lenient; 01 §12 + 09 §6: D-P5-13..16; 09: v1.1 slot (D-P6-5)
- 10 README: holdout table as measured, ceiling framing, no "beats keyword
  search"; QWK 0.829 human subset; LLM-proposed labels; 0/345 self-authored;
  LLM-LLM 0/1 drift 23/103; pooled-recall bias; tuning overfit (D-P6-4)
- Project instructions: delete Doc 12 trigger (D-M-3); invariant 15 ->
  D-P5-13..16; invariant 11 -> 41,899 chunks
- 02 §5 + storage budget (41,899 chunks), Phase 7
- Vector nomination 596 ms (Phase 7); normalize.py docstring; 01 §8 strata
- #6922 in_corpus; 05 §3 --flag color contrast
