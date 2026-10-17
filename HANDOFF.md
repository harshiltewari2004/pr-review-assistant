# Handoff — Day 39 close (v1.1: corpus fixed)

## State
- main, pushed, clean tree. Tests: 128 passed. Last tag v0.4-demo-page.
- LIVE page: https://harshiltewari2004.github.io/pr-review-assistant/
- LIVE bot:  github.com/harshiltewari2004/p5-pr-review-demo
- v1.0 holdout (D-P6-4): lenient R@3 0.321, ceiling 0.501, top-1 8/10.
- v1.1: protocol D-V11-1 (36f4be1), queries D-V11-2 (5c3c72b),
  prune step D-V11-3 (e712277). Follow D-V11-1's ORDER.
- v1.1 CORPUS FINAL: fingerprint d7283c3a; in_corpus 3,148; chunks 37,907;
  local == Neon (day36_compare_corpora content 0f7e8794).
- v1.0 corpus now ONLY in ~/backups/prreview_v1_0_b04b9a89.dump: v1.0
  numbers re-run only after a restore.
- Shell: run gh / git push with `env -u GITHUB_TOKEN`. zsh
  interactivecomments is on. In double-quoted psql never write `!~`
  (zsh history expansion): use NOT (x ~ y).

## Gate
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check . && pytest -q
python -m eval.snapshot   # must print d7283c3a

## DONE Day 39
- chunking.py: MINIFIED_SUFFIX + BUILT_BUNDLES / VENDORED_P5_SOUND /
  GENERATED_DOCS_DATA in EXCLUDED_PATH_PATTERNS (f9012c0). Test through
  parse_hunks (vendored_excluded.diff); 5 teeth checks incl. over-exclusion.
- index_repo.py step 5a prune_chunks (D-V11-3). 3rd run: stale 0, and the
  fingerprint did not move with indexed_at (content-addressed).
- Applied local + Neon; survivors hash identical on both; snapshot d814f93.

## NEXT SESSION (D-V11-1 step 3: pools)
1. Read eval/pool.py and the tune.py grid: v1.1 reuses that code path.
2. pool_v11.json per D-V11-1 §3 over all 40 queries; record d7283c3a.
3. Count NEW pairs (not among the 345 graded): this sizes labeling.
Then author's 30 -> grader -> kappa -> tune -> holdout once.
~6 sessions remain (7 if labeling splits).

## Open
- Upkeep: GitHub actions -> Node 24 versions
- Pooling bias (README limitation)

## Owed
- 04: deployment -> D-P7-3; 04 §5: step 5a prune (D-V11-3)
- 05: D-P8-1..5 deviations; 01 §11 -> lenient headline
- 01 §12 + 09 §6: D-P5-13..16; 09: v1.1 slot (D-P6-5, D-V11-1)
- 10 README: v1.0 and v1.1 tables as measured, ceiling framing; QWK human
  subset; LLM-proposed labels; live page + bot links; files_changed/totals
  differ from GitHub on PRs touching excluded files (D-P2-14)
- Project instructions: delete Doc 12 trigger (D-M-3); invariant 15 ->
  D-P5-13..16; invariant 10 -> idempotent AND convergent (D-V11-3);
  invariant 11 -> 37,907 chunks; deployment invariants -> D-P7-3
- 02 §5 + storage budget (37,907 chunks); normalize.py docstring; 01 §8 strata
- #6922 in_corpus
