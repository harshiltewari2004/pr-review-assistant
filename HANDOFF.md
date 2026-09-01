# Handoff — 2026-08-25, Day 24 close (Sessions A + B)

## State
- HEAD: `ce51b93` on `main`, pushed, clean tree
- Tests: **66** passing (`pytest tests/unit -q`)
- `ruff check` clean, `ruff format` clean
- Local Docker Postgres; Neon untouched this session
- `09` Days 1–23 COMPLETE. Day 24 complete. **26 calendar days used —
  three days behind, not one.**

## Gate before writing code
```bash
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain          # expect empty
git log --oneline -1            # expect <new hash>
ruff check                      # expect clean
pytest tests/unit -q            # expect 66
python -c "import os; print(len(os.environ['DATABASE_URL_DIRECT']))"   # expect 140
```
Use the Python check, not `echo ${#VAR}` — echo passes on an unexported shell
variable. `psql` needs `DATABASE_URL_LOCAL`; repo_id = **2**.

## ⚠️ Invariant 2 is violated in running code
Every piece to close it exists. Nothing calls them in sequence.
`build_candidate_set()` is nomination-only: the three dicts have divergent key
sets. **The orchestrator is the fix and it is the first thing next session.**

## Built this session
`signals.py`
- `file_overlap_signal()` — uncapped by design (D-P4-7). Run once on #8994:
  148 candidates, all J > 0.0. Closes the reference-location gap.
- `vector_backfill_for_pr()` + `VECTOR_BACKFILL_SQL` — `ANY($5::bigint[])`,
  no ORDER BY, no LIMIT. **Never executed.**
- `bm25_scores()` — uncut, no `> 0.0` guard. `bm25_signal()` refactored to a
  thin cut over it; invariant 1 now enforced once per signal. Six golden
  assertions survived.

`scoring.py`
- `CandidateSet`, `_nominate()` with `(-score, pr_id)`, `build_candidate_set()`
- `rank_candidates()` — pure; normalises all three over `candidates.ids`,
  weighted sum, top 3. **Never executed.**

`normalize.py`
- `min_max_normalize(raw, candidate_ids)` — `candidate_ids` explicit, not
  inferred from `raw.keys()`. Extra keys in `raw` ignored; missing keys raise.

`constants.py` — `FILE_OVERLAP_TOP_K = 100`
`tests/` — `test_scoring.py` (2), `test_normalize.py` (5)
`scripts/day24_file_overlap.py` — spike

## 🎯 NEXT SESSION — fixed order

1. **Doc 12 ritual — `signals.py`** (3 days lagged), then **`normalize.py`**.
   Answer-and-reasoning form, not the quiz in `12 §3` steps 10–12. **Two hours
   allocated. Do this first.**
2. **The orchestrator.** Async, in `scoring.py`. Three signals → union →
   three backfills → `rank_candidates()`. First run will raise
   `"backfill did not run"` until wired correctly — **that raise is correct.**
   Register a `|C|` prediction in `JOURNAL.md` before running.
   `scoring.py`'s own Doc 12 ritual comes due after this.
3. **`test_retrieval.py`.** `07 §4`'s temporal filter requirement is
   **HALF-MET.** The union property is proven in `test_scoring.py`; the
   end-to-end property — no result post-dates the query, over the fixture
   corpus — has no test and `tests/integration/` is empty. **Do not record
   the Day-24 deadline as met.** `07 §6` allows exactly two integration
   files; this is one of them.

## Owed, not blocking
- `#6922` Swedish translation — confirm which files, `07 §4`
- `patch-vector.js` — 6 PRs touch it, none reached k=3, unexamined
- Ledger drift: open PRs 126 → 105, cause unknown
- `_validate_embedding()` — shape check now duplicated in `vector_signal()`
  and `vector_backfill_for_pr()`
- `test_query_pr_never_retrieves_itself` is unfalsifiable as written
- D-P4-5 tokenizer — **"DO NOT fix after Day 25"**, still unfixed
- D-P5-2 anchors, D-P5-3 dual-branch port pairs

## Doc-revision batch (one pass, not piecemeal)
- `01 §2` "approximately 4,175 **closed** PRs" — 105 open PRs are in corpus
- `constants.py` `VECTOR_TOP_K` comment — D-P4-8, two layers
- `CANDIDATE_TOP_N` — names a concept the design does not have; check
  `git log -S CANDIDATE_TOP_N` then delete
- `HF_SPACE_URL` in `.env` and `.env.example` — dead since Day 1
- D-P4-4 threshold — absolute or percentile, in `constants.py`
- `vector_signal_for_pr()` docstring — "~350 ms (Day 17)", superseded twice,
  now ~920 ms
- Docstring garbles: `MEMEBERSHIP`, `memberships list`,
  **`Union but intersection`** (asserts the opposite of invariant 3),
  `teh`, `evvery`, `atleast`, `on` vs `ON` in `VECTOR_BACKFILL_SQL`

## Fatigue note
Threshold passed mid-Session A; errors ran prose → indentation → naming across
both sessions. **Comprehension never degraded** — the median-of-1 finding, the
25-way tie, and the teeth-check reading all came from correct output analysis.
Typing did. Two type-by-hand modules in one session is over budget.