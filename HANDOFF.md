# Handoff — Day 38 close (v1.1: queries drawn)

## State
- main, pushed, clean tree. Tests: 127 passed. Last tag v0.4-demo-page.
- LIVE page: https://harshiltewari2004.github.io/pr-review-assistant/
- LIVE bot:  github.com/harshiltewari2004/p5-pr-review-demo
- v1.0 holdout (D-P6-4): lenient R@3 0.321, ceiling 0.501, top-1 8/10.
- v1.1 protocol PRE-REGISTERED: D-V11-1 (36f4be1). Follow its ORDER.
- v1.0 corpus backed up: ~/backups/prreview_v1_0_b04b9a89.dump (99 MB).
- Corpus fix measured: 236 PRs touched, 48 emptied (3,196 -> 3,148),
  3,992 chunks removed; 0 eval queries, 0 judged candidates emptied.
- In this shell, .env's GITHUB_TOKEN is read-only: run gh / git push with
  `env -u GITHUB_TOKEN`.

## Gate
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check . && pytest -q
python -m eval.snapshot   # must still print b04b9a89: corpus not yet changed

## DONE Day 38
- Migration 003 (cohort) on local + Neon. v1.0 readers filter cohort 'v1.0'.
- 20 v1.1 holdout queries written (D-V11-2, 5c3c72b); v1.0 draw reproduced.

## NEXT SESSION (D-V11-1 step 1: corpus fix)
1. chunking.py: GENERATED/VENDORED exclusion rule (D-V11-1 §1) + a test
   through parse_hunks (fixture with lib/p5.js, *.min.js, parameterData.json
   blocks next to a real src/ block) + teeth check.
2. Re-parse all PRs from .cache/ through the real path: drop removed
   chunks, recompute files_changed/additions/deletions (D-P2-14), step 4b.
   Golden: in_corpus 3,148; chunks 37,907; 0 eval queries emptied;
   remaining chunk content + embeddings unchanged.
3. New fingerprint; apply to Neon; local-vs-Neon content check.
Then pools -> author's 30 -> grader -> kappa -> tune -> holdout once.

## Open
- Upkeep: GitHub actions -> Node 24 versions
- Pooling bias (README limitation)

## Owed
- 04: deployment -> D-P7-3; 05: D-P8-1..5 deviations; 01 §11 -> lenient headline
- 01 §12 + 09 §6: D-P5-13..16; 09: v1.1 slot (D-P6-5, D-V11-1)
- 10 README: v1.0 and v1.1 tables as measured, ceiling framing; QWK human
  subset; LLM-proposed labels; live page + bot links
- Project instructions: delete Doc 12 trigger (D-M-3); invariant 15 ->
  D-P5-13..16; invariant 11 -> chunk count; deployment invariants -> D-P7-3
- 02 §5 + storage budget; normalize.py docstring; 01 §8 strata
- #6922 in_corpus
