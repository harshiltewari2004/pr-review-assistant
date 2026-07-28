# PR Review Assistant — Testing

**v1.1 — Locked July 2026**

*Changed from v1.0: added §3, golden assertions written at build time (`11_workflow.md` §8). Subsequent sections renumbered.*

Don't aim for 100% coverage — aim for the cases that actually fail.

---

## 1. Two quality systems, never confused

This project has **two separate mechanisms** for quality, and conflating them is the most likely testing mistake.

| | Tests | Evaluation harness |
|---|---|---|
| **Question** | Does the code do what it says? | Are the results any good? |
| **Verdict** | Pass / fail | A number with a confidence interval |
| **Lives in** | `tests/` | `eval/` |
| **Runs** | On every change | When tuning or reporting |
| **Owner doc** | This one | `01_evaluation_protocol.md` |

**No test asserts retrieval quality.** A test that says *"PR #15992 must rank first for query #16024"* looks reasonable and is wrong — it hard-codes a subjective judgment into the build, and it will fail every time weights are tuned, training you to ignore failures.

Retrieval quality is measured by Recall@3 and MRR against labeled judgments. That is the harness's entire job. Tests verify that normalization produces values in `[0, 1]`, not that the ranking is good.

---

## 2. What gets tested

| Component | Test? | Why |
|---|---|---|
| **Diff parsing / chunking** | **Yes — heavily** | Highest edge-case density in the codebase; failures are silent |
| **Per-query normalization** | **Yes** | Pure function, cheap to test, silent degradation if wrong |
| **Jaccard file overlap** | **Yes** | Pure function, trivial edge cases that are easy to get wrong |
| **Temporal filter** | **Yes — mandatory** | A correctness invariant; a leak invalidates every published number |
| **Corpus filter** | **Yes** | Label prefix matching has already produced one real bug |
| **BM25 tokenization** | **Yes** | Sub-token splitting is subtle and silently loses matches |
| **Reason template ordering** | **Yes** | First-match-wins; priority inversions produce wrong-but-plausible text |
| **Chunk → PR aggregation** | **Yes** | Both `MAX` and mean-of-top-3 paths |
| Embedding model output | No | Testing it tests Hugging Face, not this project |
| FastAPI routing | No | Framework boilerplate |
| CRUD SQL passthrough | No | Exercised by integration tests anyway |
| Frontend | No | One page, visual — manual check across states |
| Exact score values | **Never** | Brittle by construction; changes with every weight tune |

---

## 3. Golden assertions — the floor

**Three lines per stage, written at the moment you build the stage.** These are the minimum that exists regardless of what else slips.

The reasoning comes from a prior project's retrospective (`11_workflow.md` §5): the expensive bugs were **silent data-shape bugs**, not logic errors — a dropped field, a wrong separator character, a wrong key shape. A full test suite would not have caught most of them. **A single assertion pinned to each stage's output shape would have caught several.**

| Stage | Assertion | Written in |
|---|---|---|
| **Chunking** | Fixture diff → exact expected hunk count; first hunk's `file_path`; header has no line numbers | Phase 2 |
| **Embedding** | Output is exactly 384 dimensions; L2 norm ≈ 1.0 | Phase 3 |
| **Retrieval** | Three known query PRs return non-empty results, all predating the query | Phase 3 |
| **Normalization** | Output bounded `[0, 1]`; `max == min` returns all zeros | Phase 6 |
| **Scoring** | `final_score ∈ [0, 1]` with weights summing to 1.0 | Phase 6 |

These are not a substitute for §4 — they are the subset that must never be deferred. A stage without its golden assertion is not finished.

**They also encode the general rule:** print and read a stage's output rather than inferring correctness from the absence of an error. Every failure mode in this project produces plausible-looking output and no exception.

---

## 4. Critical invariants

These must have tests. Everything else is optional.

**Chunking**
- A hunk header's line numbers are stripped; its trailing context is retained
- `@@` appearing *inside* diff content does not split a hunk — headers anchor to line start only
- Binary files, deleted files (`+++ /dev/null`), and renames with no content change produce zero chunks
- Excluded extensions (`.md`, `.lock`, `.svg`) produce zero chunks even inside an in-corpus PR
- An empty diff produces zero chunks and does not raise
- `hunk_index` is sequential per file, starting at 0
- `was_truncated` is `True` exactly when `token_count > 256`

**Normalization**
- Output is always within `[0, 1]`
- `max == min` returns `0.0` for every candidate, never `NaN` and never division by zero
- A single-candidate set does not raise
- Relative ordering is preserved

**Scoring**
- With weights summing to 1.0 and normalized inputs, `final_score ∈ [0, 1]`
- All three signals are normalized over the **same** candidate set

**Temporal filter**
- No candidate with `created_at >= query.created_at` ever appears in a candidate set
- The query PR never retrieves itself

**Corpus filter**
- A PR whose diff is only `.md` files leaves zero hunks and is marked `in_corpus = FALSE`, `exclusion_reason = 'no_source_content'` (`04_architecture.md` §5 step 4b)
- A PR carrying a `Documentation` label **and** a substantive `.js` change stays in corpus — the exclusion is on content, not on the label
- A translation-only PR touching `translations/*/translation.json` leaves zero hunks; `translations/dev.js` and `translations/index.js` do not
- Bot authors excluded by `author_type` as the primary rule, so a new bot account is caught without a code change
- The explicit account list (`p5js-bot`, `allcontributors`, …) is an **additive** second rule, tested separately — a bot-shaped account that GitHub reports as `author_type = 'User'` must still be excluded
- A duplicate resubmission triple (`#8947`/`#8946`/`#8945`) leaves exactly one PR in corpus, and it is the merged one


**Jaccard**
- Identical sets → `1.0`; disjoint sets → `0.0`; either set empty → `0.0`, not a division error

**Tokenization**
- `jsonable_encoder` emits the whole identifier **and** `jsonable`, `encoder`
- `formatSseEvent` splits on camelCase boundaries

---

## 5. Layout

```
tests/
├── conftest.py                  # fixtures, test DB setup
├── unit/
│   ├── test_chunking.py         # the big one
│   ├── test_normalize.py
│   ├── test_signals.py          # jaccard, tokenization
│   ├── test_scoring.py
│   ├── test_corpus_filter.py
│   └── test_reasons.py
├── integration/
│   ├── test_index_pipeline.py   # diff → chunks → vectors in DB
│   └── test_retrieval.py        # end-to-end on a fixture corpus
└── fixtures/
    ├── diffs/                   # real diffs from fastapi/fastapi
    │   ├── simple_single_file.diff
    │   ├── multi_file.diff
    │   ├── binary_file.diff
    │   ├── deleted_file.diff
    │   ├── rename_only.diff
    │   ├── at_marker_in_content.diff
    │   └── huge_hunk.diff       # >256 tokens, triggers truncation
    └── prs.json                 # 5 PR records for the fixture corpus
```

**Fixtures are real diffs, committed to the repository.** Synthetic diffs miss exactly the formatting quirks that break parsers. Pull them from `fastapi/fastapi` during Phase 1's data-access spike and save them — the spike is already fetching real diffs, so this costs nothing extra.

`at_marker_in_content.diff` is the one people forget: a diff whose *content* contains `@@` will split incorrectly under a naive parser.

---

## 6. Integration tests

Two, and only two.

**`test_index_pipeline.py`** — index the 5-PR fixture corpus end to end, then assert:
- Expected chunk count
- Every chunk has a non-null 384-dimension embedding
- **Re-running produces no duplicates** — the `UNIQUE (pr_id, file_path, hunk_index)` idempotency guarantee. Indexing *will* be interrupted and restarted; this is the test that proves recovery works.

**`test_retrieval.py`** — query the fixture corpus and assert:
- Exactly 3 results returned (or fewer, if the corpus is smaller)
- No result post-dates the query
- Every result carries all three normalized signal scores
- Every result has a non-empty reason string

Note what these assert: **structure, not ranking.** No assertion about which PR comes first.

---

## 7. Test database

Local Postgres + pgvector via `docker-compose.yml`. **Never Neon.**

- Migrations applied fresh per session
- Each test runs in a transaction that rolls back
- No network dependency — tests must run offline

Running tests against Neon would consume free-tier compute hours and risk writing into the corpus the eval harness depends on.

---

## 8. Tooling

```bash
pytest                      # everything
pytest tests/unit -q        # fast loop while developing
pytest --lf                 # last failures only
```

`pytest` + `pytest-asyncio`. No coverage tooling, no coverage gate — a percentage target encourages tests of trivial getters while the chunking edge cases stay untested.

`hypothesis` is optional and worth 20 minutes on the normalization function alone, where property-based testing fits naturally (*output always in `[0,1]` for any input*).

---

## 9. When to write them

Not all on day 1, and not all at the end.

| Phase | Testing work |
|---|---|
| **2** (ingest, chunking) | Write `test_chunking.py` **as you write the parser.** It is a pure function with heavy edge cases — the cheapest possible testing, and the parser is where you will actually lose time to bugs. |
| **3** (vector skeleton) | Add the two integration tests once the pipeline runs end to end |
| **4** (three signals) | Add `test_normalize.py`, `test_signals.py`, `test_scoring.py` alongside the code |
| **6** (hybrid) | Temporal filter test **before** pooling begins — a leak discovered after labeling means relabeling |
| **9** (final) | Fill gaps against §4. Do not start writing tests here. |

The temporal filter test is the one with a hard deadline. Everything else can slip; that one cannot, because it invalidates hand-labeled work that costs hours to redo.

---

## 10. Checklist

- [ ] No test asserts which PR ranks first
- [ ] **Every stage has its golden assertion, written when the stage was built**
- [ ] **Each stage's output printed and read at least once, not inferred from absence of errors**
- [ ] Real diff fixtures committed, including the `@@`-in-content case
- [ ] Chunking tests written during Phase 2, not retrofitted
- [ ] Temporal filter tested before Phase 5 labeling begins
- [ ] Normalization handles `max == min` without raising
- [ ] Re-indexing idempotency proven by integration test
- [ ] Tests run offline against local Postgres, never Neon
- [ ] No coverage gate configured
