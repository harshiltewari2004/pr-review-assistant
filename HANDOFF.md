# Handoff — Day 34 close

## State
- main, pushed, clean tree. Tests: 92 passed, 1 skipped. Ruff clean.
- Labels final: round 1 = 345, round 2 = 98; official = latest round.
  Agreement (author's 30): QWK 0.829, lenient 0.865, strict 0.586.
  HEADLINE = lenient Recall@3 (D-P5-15).
- eval/score.py done (D-P5-17). Tune baseline at 0.5/0.3/0.2:
  lenient 0.324 [0.292, 0.361] (ceiling 0.451), strict 0.694, MRR@3 0.900.
- Holdout SEALED: no holdout_scored.json. Never run --holdout-once until locked.

## Gate
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check . && pytest -q
python -m eval.snapshot
git status --porcelain
python -m eval.score 2>&1 | grep -v INFO | tail -7
ls eval/artifacts/holdout_scored.json

## NEXT SESSION
1. tests/unit/test_score.py: recall_at_k, recall_ceiling, reciprocal_rank
   (incl. None cases), bootstrap_ci determinism, parse_weights rejects a
   bad sum; teeth check on each.
2. PRE-REGISTER the Phase 6 tuning objective (D-P6-1x) BEFORE any tuning:
   lenient R@3 is ceiling-bound (4/10 tune queries at ceiling), strict
   has room but kappa 0.586. Options: lenient R@3 with MRR@3 tie-break;
   ceiling-normalized lenient; strict. Decide the grid and tie-break too.
3. Then Phase 6: tune on TUNE only, MAX vs mean-of-top-3, lock weights in
   constants.py with the date, holdout --holdout-once exactly once.

## Open
- D-P4-11 blocks reasons.py
- Pooling bias: the pool includes hybrid_default's top 6 (README limitation)

## Owed
- 01 §11: headline -> lenient; 01 §12 + 09 §6: D-P5-13..16
- 10 README: lenient headline + ceiling; QWK 0.829 (30-pair blind human
  subset); LLM-proposed labels; 0/345 self-authored; LLM-LLM 0/1 drift
  23/103; pooled-recall bias
- Project instructions: delete Doc 12 trigger (D-M-3); invariant 15 ->
  D-P5-13..16; invariant 11 -> 41,899 chunks
- 02 §5 + storage budget (41,899 chunks), Phase 7
- Vector nomination 596 ms (Phase 7); normalize.py docstring; 01 §8 strata
- #6922 in_corpus; 05 §3 --flag color contrast
