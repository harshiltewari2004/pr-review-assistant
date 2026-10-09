# Handoff — Day 33 close

## State
- main, pushed, clean tree. Tests: 92 passed, 1 skipped. Ruff clean.
- All 345 pairs judged, round 1: batch 1 170 (Claude, this chat), batch 2
  175 (author's 30 official + 145 from a fresh chat outside the project)
- D-P5-14 kappa (n=30): 3-grade 0.628, QWK 0.774, lenient 0.865, strict 0.380
- D-P5-15 chosen: corrected rule, re-grade the 1/2 boundary as round 2
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
python -m eval.agreement | head -4

## NEXT SESSION: D-P5-15 (~1 session)
1. psql "$DATABASE_URL_LOCAL" -c '\d judgments'
   Check the round CHECK constraint and unique key allow round 2 per pair.
2. Script: dump every Claude-graded round-1 pair at grade 1/2, author's 30
   excluded, in label.py's blind display, WITHOUT the round-1 grade.
3. Fresh chat OUTSIDE the project, same model: dump + 01 + corrected rule.
4. Import as round 2 (import script needs --round); then official-label
   logic: round 2 > round 1; author's 30 always official.
5. agreement.py against round-2 grades -> kappa; record the headline call.
Then eval/score.py (TYPED, piece by piece): Recall@3 strict/lenient, MRR,
bootstrap CI over queries, fingerprint refusal (W2), unjudged explicit (W3),
reads OFFICIAL labels.

## Open
- D-P5-15 result + headline (strict vs lenient)
- D-P5-9 W3: Phase 6 unjudged rate of tuned top-3 must be 0
- D-P4-11 blocks reasons.py

## Owed
- Project instructions: invariant 15 -> D-P5-13/14/15 wording; invariant 11 -> 41,899 chunks
- 01 §12 + 09 §6: record the D-P5-13/14 protocol change
- README: LLM-proposed labels, human subset kappa, 0/345 self-authored
- 02 §5 + storage budget (41,899 chunks), Phase 7
- Vector nomination 596 ms (Phase 7); normalize.py docstring; 01 §8 strata
- #6922 in_corpus; 05 §3 --flag color contrast
