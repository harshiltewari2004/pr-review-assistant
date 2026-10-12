# Handoff — Day 35 close

## State
- main, pushed, clean tree. Tests: 121 passed, 0 skipped (07 §6 now real).
- Phase 6 DONE, tagged v0.2-hybrid. Weights LOCKED 0.6/0.3/0.1, max (D-P6-2).
- Holdout scored ONCE (D-P6-4): lenient R@3 0.321 [0.237, 0.421], ceiling
  0.501; strict 0.542; MRR@3 0.883 (top result relevant 8/10). Tuning
  overfit (prior 0.36, bm25 0.35); nothing re-tuned (invariant 14).
- reasons.py DONE (D-P4-11 resolved, D-P4-15): 03 §10 templates, explain().
- v1.1 eval expansion scheduled before Phase 9, headline pre-committed (D-P6-5).

## Gate
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check . && pytest -q
python -m eval.snapshot
git status --porcelain

## NEXT SESSION: Phase 7 — Deploy and Action (09 §3, ~5 sessions)
Read 04 (architecture) + 08 §8 (skeleton deploy) first.
1. POST /analyze + GET /similar/... wired: find_similar_prs + explain.
2. Comment format: title + link + reason per result (D-P4-15 observation).
3. Cloud Run: CPU-only torch in the Dockerfile (inv. 23), $PORT default 7860
   (inv. 22), US region (inv. 25), Secret Manager (inv. 24), model baked in.
4. GitHub Action: own token, continue-on-error (inv. 26), warmup loop.
5. Measure cold start; revisit the ANN decision at 41,899 chunks (inv. 11).

## Open
- D-P3-2: asyncpg pool under Cloud Run instance churn (Phase 7)
- Pooling bias (README limitation)

## Owed
- 01 §11: headline -> lenient; 01 §12 + 09 §6: D-P5-13..16; 09: v1.1 slot
- 10 README: holdout table as measured, ceiling framing, no "beats keyword
  search"; QWK 0.829 human subset; LLM-proposed labels; 0/345 self-authored;
  LLM-LLM 0/1 drift 23/103; pooled-recall bias; tuning overfit (D-P6-4)
- Project instructions: delete Doc 12 trigger (D-M-3); invariant 15 ->
  D-P5-13..16; invariant 11 -> 41,899 chunks
- 02 §5 + storage budget (41,899 chunks), Phase 7
- Vector nomination 596 ms (Phase 7); normalize.py docstring; 01 §8 strata
- #6922 in_corpus; 05 §3 --flag color contrast
