# Handoff — Day 37 close (v1.1 started)

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
python -m eval.snapshot   # must still print b04b9a89: NOTHING changed yet

## NEXT SESSION (D-V11-1 steps 2, then 1)
1. Migration 003: eval_queries.cohort ('v1.0' for the existing 20).
2. select_queries.py: continuation mode on the v1.0 corpus (SEED=28, same
   strata/allocation/eligibility). Skip EXCLUDED_NUMBERS, 01 §7 anchor PRs,
   any PR number found in tests/ scripts/ JOURNAL.md DECISIONS.md frontend/.
   Dry run -> read the 20 -> write cohort 'v1.1'. Commit before step 3.
3. Corpus fix through the real ingest path from .cache/ (chunking.py
   exclusion rule + re-parse + step 4b). Golden: 3,148 in corpus,
   37,907 chunks, 0 queries emptied; remaining chunk content unchanged.
4. New fingerprint; then Neon; repeat the local-vs-Neon content check.
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
