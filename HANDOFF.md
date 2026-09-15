# Handoff — 2026-09-01, Day 25 close

## State
- HEAD: <hash> on `main`, pushed, clean tree
- Tests: **69** passing (`pytest tests/unit -q`)
- `ruff check` clean, `ruff format` clean
- Day 25 complete. Seven-day hospital gap between Day 24 and Day 25 —
  **track position in SESSIONS, not calendar days.** 26 sessions remain.

## Gate before writing code
```bash
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain          # expect empty
ruff check && ruff format --check .
pytest tests/unit -q            # expect 69
python -c "import os; print(len(os.environ['DATABASE_URL_DIRECT']))"   # expect 140
```
`ruff format --check` added — Day 25 found drift the old gate missed.
`psql` needs `DATABASE_URL_LOCAL`; repo_id = **2**.

## ⚠️ Invariant 2 still violated in running code
Unchanged from Day 24. Every piece exists; nothing calls them in sequence.

## 🎯 NEXT SESSION — fixed order, no substitutions
1. **`test_retrieval.py`.** `07 §4`'s temporal filter requirement is
   HALF-MET and `tests/integration/` is empty. `07 §6` allows exactly two
   integration files; this is one. **Day-24 deadline, missed, still owed.**
2. **The orchestrator.** Async, in `scoring.py`. Three signals → union →
   three backfills → `rank_candidates()`. Register a `|C|` prediction in
   `JOURNAL.md` first. The `"backfill did not run"` raise is correct.
   Measure backfill latency on the first run — that resolves D-P4-10.
3. Combined Doc 12 ritual: `normalize.py` + `scoring.py`.

**No ritual before item 1.** Day 25 was a full ritual day; a second one
would make the ritual avoidance rather than review.

## Day 25 output
- D-P4-5 RESOLVED inside its deadline. `tokenize()` drops length-1
  sub-tokens after the gate. avgdl 146.2 → 135.66, vocab 19,442 → 19,441,
  floored 13 → 11 (`p5` retained). Prediction held 4 of 4.
- `rank-bm25` verified from source: no `k3` query saturation. D-P4-9.
- Doc 12 ritual COMPLETE for `signals.py`, all 12 steps. Backlog cleared.
- New: D-P4-9, D-P4-10, D-P4-11, D-M-1.

## Owed, not blocking
- `#6922` Swedish translation — confirm which files, `07 §4`
- `patch-vector.js` — 6 PRs touch it, none reached k=3
- Ledger drift: open PRs 126 → 105, cause unknown
- `_validate_embedding()` — shape check duplicated in two functions
- `test_query_pr_never_retrieves_itself` unfalsifiable as written
- D-P5-2 anchors, D-P5-3 dual-branch port pairs
- Own-words summary of `signals.py` into `logs/` (D-M-1 mitigation)

## Doc-revision batch
- **D-P4-11 first — it changes behaviour, the rest are wording**
- `01 §2` "approximately 4,175 **closed** PRs" — 105 open PRs in corpus
- `CANDIDATE_TOP_N` — unused; `git log -S` then delete
- `HF_SPACE_URL` — dead since Day 1
- `vector_signal_for_pr()` docstring "~350 ms (Day 17)" → ~920 ms
- **New rule: keep the *why* in docstrings, move *numbers* to JOURNAL.md
  with a date.** Reasoning is stable; measurements rot.
- Garbles: `temporarily-eligible`, `scorse`, `anomally`, `fillng`,
  `vector_signal_pr()`, `atleast` ×2, `Union but intersection`
  (asserts the opposite of invariant 3), `on` vs `ON`

## Fatigue note
Long session, no code-transcription errors. The one hand-typed change was
one line, verified against six expected outputs before commit. Reading and
reasoning after a hospital week was the right allocation.