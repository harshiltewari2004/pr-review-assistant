# Handoff — Day 34 close

## State
- main, pushed, clean tree. Tests: 92 passed, 1 skipped. Ruff clean.
- Judgments: round 1 = 345, round 2 = 98. OFFICIAL label = latest round
  per pair (the author's 30 have no round 2, so they stay official).
- Agreement on the author's 30 (D-P5-16 policy): QWK 0.829, lenient 0.865,
  strict 0.586. HEADLINE = LENIENT Recall@3 (D-P5-15 pre-registered bar).
- Corpus fingerprint b04b9a89 (4,372 / 3,196 / 41,899)

## Gate
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check . && pytest -q
python -m eval.snapshot
git status --porcelain
psql "$DATABASE_URL_LOCAL" -c "SELECT round, count(*) FROM judgments GROUP BY round"

## NEXT SESSION: eval/score.py (TYPED, piece by piece)
- Reads OFFICIAL labels (DISTINCT ON pair, ORDER BY round DESC)
- Lenient Recall@3 (headline) + strict Recall@3 + MRR, tune and holdout
- Bootstrap 95% CI over QUERIES, 1,000 iterations (01 §14)
- Refuses on corpus fingerprint mismatch (D-P5-9 W2)
- Unjudged / skipped pairs handled explicitly (W3)
- Predict before running (01 §14); record in JOURNAL

## Open
- D-P5-9 W3: Phase 6 unjudged rate of tuned top-3 must be 0
- D-P4-11 blocks reasons.py

## Owed
- 01 §11: headline -> lenient (D-P5-15 result); 01 §12 + 09 §6: D-P5-13/14/15/16
- 10 README template: lenient headline; kappa = QWK 0.829 on a 30-pair
  blind human subset; LLM-proposed labels; 0/345 self-authored;
  LLM-vs-LLM 0/1 drift (23/103) as a limitation
- Project instructions: delete the Doc 12 trigger (D-M-3); invariant 15 ->
  D-P5-13..16 wording; invariant 11 -> 41,899 chunks
- 02 §5 + storage budget (41,899 chunks), Phase 7
- Vector nomination 596 ms (Phase 7); normalize.py docstring; 01 §8 strata
- #6922 in_corpus; 05 §3 --flag color contrast
