# Handoff — Day 31 close

## State
- HEAD: <fill in after commit> on `main`, pushed, clean tree
- Tests: 92 passed, 1 skipped
- judgments: 0 rows. Batch 1 = 170 pairs, batch 2 = 175 (D-P5-11)
- 01 §7: 9 p5.js anchors + 6 rules (D-P5-12)
- Corpus fingerprint b04b9a89… (4,372 PRs, 3,196 in corpus, 41,899 chunks)
- #8994 baseline: #8259 0.9255, #6222 0.8914, #8821 0.8850

## Gate
```bash
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
git log --oneline -3
ruff check && ruff format --check .
pytest -q
psql "$DATABASE_URL_LOCAL" -c "SELECT count(*) FROM judgments"
python -m eval.label --batch 1 --plan | tail -1
```

## 🎯 NEXT SESSION — batch 1, ONE sitting (~2.5 h)
1. Calibrate: re-read 01 §3, §4, §7. Keep §7 open beside the terminal.
2. Smoke test: one real judgment, `q`, audit the row (round 1, batch 1,
   self_authored false); --plan shows 169 remaining.
3. Label the rest. 4 questions + 6 rules per pair. 5-min break if
   over-2x warnings cluster. Paste the summary.
4. Note the date. Re-test (~50 from batch 1) is due ONE WEEK later.

## Gap week (after batch 1, before re-test)
- eval/score.py (typed): Recall@3 strict/lenient, MRR, bootstrap CI;
  MUST refuse on corpus fingerprint mismatch (D-P5-9 W2); unjudged and
  skipped pairs handled explicitly (W3).
- Milestone B / B′ (09 §4).

## Open
- D-P5-9 W3: Phase 6 unjudged rate of tuned top-3 must be 0.

## Owed
- Re-upload docs 01, 02, 03, 09, 10 to Claude project knowledge
- Project instructions, hot invariant 11: "~10k chunks" -> 41,899 measured
- ⚠️ 02 §5 contradicts itself (41,899 chunks vs "single-digit ms");
  rewrite with Phase 7 measurements alongside the ANN decision
- 02 storage budget table assumes 10,000 chunks (actual 41,899)
- Vector nomination 596 ms — per-chunk-scan hypothesis (Phase 7)
- normalize.py docstring: degenerate-0.0 reason is 03 §10 thresholds
- 01 §8: replace FastAPI-era subsystem list with D-P5-5 path strata
- #6922: in_corpus open item
- README limitations: label coverage, docs-only queries excluded, #5460,
  pool-relative recall, 0/345 self-authored

  - 05 §3: --flag #E8590C -> #C2410C (white badge text fails 4.5:1)
- 09 checklist: Milestone B′ done Day 31 (verdict A)