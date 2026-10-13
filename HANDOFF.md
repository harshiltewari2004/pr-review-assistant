# Handoff — Day 36 close

## State
- main, pushed, clean tree. Tests: 127 passed. Tagged v0.3-live-bot.
- LIVE: github.com/harshiltewari2004/p5-pr-review-demo. A PR there gets a
  bot comment in ~1 min. Demo PR #2 = replay of p5.js #9281 (strong result).
- Compute runs IN the GitHub Action (D-P7-3): action/entry.py ->
  app.service.analyze_diff (the same function as POST /analyze).
  Neon via read-only role pr_bot_reader (D-P7-4). Cloud Run deferred (no card);
  the Dockerfile is ready (517 MB, 7 s, graceful SIGTERM).
- Neon is content-identical to the evaluated corpus (b1ea02d3).
- In this shell, .env's GITHUB_TOKEN is read-only: run gh/git push to the
  demo repo with `env -u GITHUB_TOKEN`.

## Gate
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check . && pytest -q

## NEXT SESSION: Phase 8 — demo frontend (05_frontend.md, ~4-5 sessions)
Static page; seeded results; link the live demo repo and PR #2.
Then v1.1 (D-P6-5), then Phase 9 (README).

## Open
- v1.1 evidence: Jaccard favours single-file PRs; BM25 undervalued (D-P6-4,
  D-P7-4 finding 1)
- Upkeep: actions/checkout, setup-python, cache to Node 24 versions
- Pooling bias (README limitation)

## Owed
- 04: deployment section -> D-P7-3 (Action compute); 01 §11 -> lenient headline
- 01 §12 + 09 §6: D-P5-13..16; 09: v1.1 slot (D-P6-5)
- 10 README: holdout table as measured, ceiling framing, no "beats keyword
  search"; QWK 0.829 human subset; LLM-proposed labels; live demo link
- Project instructions: delete Doc 12 trigger (D-M-3); invariant 15 ->
  D-P5-13..16; invariant 11 -> 41,899 chunks; deployment invariants 22-25 ->
  apply to the Dockerfile, deploy now via Action (D-P7-3)
- 02 §5 + storage budget (41,899 chunks); normalize.py docstring; 01 §8 strata
- #6922 in_corpus; 05 §3 --flag color contrast
