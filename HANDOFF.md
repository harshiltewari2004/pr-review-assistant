# Handoff — Day 37 close

## State
- main, pushed, clean tree. Tests: 127 passed. Tagged v0.4-demo-page.
- LIVE page: https://harshiltewari2004.github.io/pr-review-assistant/
- LIVE bot:  github.com/harshiltewari2004/p5-pr-review-demo (PR #2 = #9281 replay)
- Holdout (v1.0, D-P6-4): lenient R@3 0.321 (ceiling 0.501), MRR@3 0.883,
  top result relevant 8/10. bm25_only 0.35, prior 0.36: tuning overfit.
- In this shell, .env's GITHUB_TOKEN is read-only: run gh / git push with
  `env -u GITHUB_TOKEN`.

## Gate
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check . && pytest -q

## NEXT SESSION: v1.1 (D-P6-5), ~3 sessions
1. FIRST: pre-register the v1.1 protocol (new D entry) before any data:
   ~20 NEW eval queries (post-snapshot or unused corpus PRs; none of the
   current 20), pooling, labels (fresh grader + corrected rule + human
   subset + kappa), tuning on all 20 OLD queries, ONE run on the new
   holdout. Headline = v1.1 holdout whether higher or lower (D-P6-5).
2. Candidate fixes, decided in that entry: exclude generated files
   (docs/parameterData.json) from chunking; Jaccard single-file bias;
   BM25 weight learned on 20 queries; optional issue-link signal.
   A corpus change -> re-embed -> NEW fingerprint; v1.0 artifacts kept.
3. score.py adds per-rank relevance (D-P8-4) inside the single run.
Then Phase 9: weekly re-index (D-P7-5), README, launch.

## Open
- Upkeep: GitHub actions -> Node 24 versions
- Pooling bias (README limitation)

## Owed
- 04: deployment -> D-P7-3; 05: D-P8-1..5 deviations; 01 §11 -> lenient headline
- 01 §12 + 09 §6: D-P5-13..16; 09: v1.1 slot (D-P6-5)
- 10 README: holdout table as measured, ceiling framing, no "beats keyword
  search"; QWK 0.829 human subset; LLM-proposed labels; live page + bot links
- Project instructions: delete Doc 12 trigger (D-M-3); invariant 15 ->
  D-P5-13..16; invariant 11 -> 41,899 chunks; deployment invariants -> D-P7-3
- 02 §5 + storage budget (41,899 chunks); normalize.py docstring; 01 §8 strata
- #6922 in_corpus
