# Handoff — Day 26 close

## State
- HEAD: <hash> on `main`, pushed, clean tree
- Tests: **72 passed, 1 skipped** (`pytest -q`); **69** in `tests/unit`
- `ruff check` clean, `ruff format --check` clean
- 24 sessions remain. Track SESSIONS, not calendar days.

## Gate before writing code
```bash
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain          # expect empty
ruff check && ruff format --check .
pytest -q                       # expect 72 passed, 1 skipped
python -c "import os; print(len(os.environ['DATABASE_URL_DIRECT']))"   # expect 140
```
`pytest -q` replaces `pytest tests/unit -q` — integration tests exist now
and need `docker compose up`. `psql` needs `DATABASE_URL_LOCAL`; repo_id = 2.

## ⚠️ Invariant 2 still violated in running code
Unchanged since Day 24. Every piece exists; nothing calls them in sequence.
The orchestrator is item 2 below.

## 🎯 NEXT SESSION — fixed order
1. **Teeth check on the three new tests. First, before anything.**
   Predict failures for each break, then run. Revert each before the next.
   - `<` → `<=` in `VECTOR_SIGNAL_SQL`
   - drop `p.id <> $4` from `FILE_CANDIDATES_SQL`
   - `<` → `<=` in `bm25_scores()`'s comprehension
   Record predicted-vs-actual in JOURNAL.md. Day 18's break-2 came in at
   2 failures against a prediction of 1 — assume the same blindness here.
   ⚠️ `git diff` must be empty before moving on. A deliberate break left
   in VECTOR_SIGNAL_SQL contaminates every number after it.
2. **The orchestrator.** Async, in `scoring.py`. Three signals → union →
   three backfills → `rank_candidates()`. Register a `|C|` prediction in
   `JOURNAL.md` first. The `"backfill did not run"` raise is correct.
   Measure backfill latency on the first run — resolves D-P4-10.
3. Combined Doc 12 ritual: `normalize.py` + `scoring.py`.

## Day 26 output
- D-P4-12 RESOLVED: temporal filter tests split by enforcement layer.
- `tests/conftest.py` created — `db` fixture via `ingest.db.connect("local")`,
  transaction rolled back in `finally`. D-P2-25 permits the import.
- `tests/integration/test_retrieval.py` — 3 tests + 1 documented skip.
- `tests/unit/test_signals.py` — BM25 temporal filter.
- Deleted `test_query_pr_never_retrieves_itself` (unfalsifiable).
- Day-24 debt closed. Phase 5 unblocked.

## Owed, not blocking
- `#6922` Swedish translation — confirm which files, `07 §4`
- `patch-vector.js` — 6 PRs touch it, none reached k=3
- Ledger drift: open PRs 126 → 105, cause unknown
- `_validate_embedding()` — shape check duplicated in two functions
- D-P5-2 anchors, D-P5-3 dual-branch port pairs
- Own-words summary of `signals.py` into `logs/` (D-M-1 mitigation)
- `bm25_scores()` correctness of surviving scores — membership only so far

## Doc-revision batch
- **D-P4-11 first — it changes behaviour, the rest are wording**
- `signals.py`: `bm25_scores()` docstring "dimension devices" → **"admission
  devices"** (semantic — it's the Day-24 nominate/score thesis)
- `signals.py`: `vector_signal_for_pr()` "~350 ms (Day 17)" → drop the number,
  move to JOURNAL.md with a date. Measured ~920 ms Day 18.
- `scoring.py`: `build_candidate_set()` "Union but intersection" → **"Union,
  not intersection"** (currently asserts the opposite of invariant 3)
- `01 §2` "approximately 4,175 **closed** PRs" — 105 open PRs in corpus
- `CANDIDATE_TOP_N` — unused; `git log -S` then delete. Referenced in
  `vector_signal_for_pr()`'s docstring; fix that line in the same pass.
- `HF_SPACE_URL` — dead since Day 1
- **Rule: keep the *why* in docstrings, move *numbers* to JOURNAL.md with a date.**
- Garbles: `temporarily-eligible`, `scorse`, `anomally`, `fillng`,
  `vector_signal_pr()`, `atleast` ×2, `on` vs `ON` (line 204)

## Fatigue note
Three one-token transcription errors in one block past midnight. Fatigue
rule invoked and the session closed rather than running the teeth check —
that check requires editing SQL constants every published number depends on.