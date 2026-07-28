# PR Review Assistant — Code Standards

**v1.2 — Locked July 2026**

*Changed from v1.1: §11 adds the CPU-only torch constraint.*
*Changed from v1.0: §12 now covers all three record-keeping files and resolves their overlap; §13 adds session discipline from `11_workflow.md`.*

Conventions for a solo 50-day build. The goal is consistency that survives interruption — you will return to this codebase after gaps, and the standards exist so past-you is legible to future-you.

---

## 1. Language and version

**Python 3.11+.** Required for the `asyncio` and typing features used throughout; also the version pinned in the Dockerfile so local and deployed behaviour match.

---

## 2. Terminology

Fix the vocabulary once. Drift here produces bugs that are hard to see because the code reads fine.

| Term | Means | Never |
|---|---|---|
| **hunk** | A `@@` block during diff parsing — a transient construct | Used for stored rows |
| **chunk** | A stored row in `chunks`, with its embedding | Used during parsing |
| **query PR** | The incoming PR being analyzed | "source", "target" |
| **candidate PR** | A past PR being scored against the query | "match", "result" until it is ranked |
| **result** | A candidate that made the top 3 | Used for unranked candidates |
| **signal** | One of vector / file overlap / BM25 | "feature", "score" |
| **score** | A numeric value from a signal | Used for a signal itself |

A hunk becomes a chunk at the moment it is persisted. Before that it is a hunk; after, a chunk. `parse_hunks()` returns hunks; `store_chunks()` takes them and produces chunks.

**Why this matters:** `03_retrieval_engine.md` distinguishes raw scores from normalized scores at a specific pipeline stage. Sloppy naming makes it possible to normalize twice or not at all, and the bug is silent — the ranking just gets quietly worse.

Raw versus normalized is always explicit in variable names: `vector_score_raw`, `vector_score_norm`. Never bare `vector_score`.

---

## 3. Git

### Branches

```
main                         # always deployable
feature/hybrid-scoring
feature/contribution-bar
fix/hunk-header-parsing
chore/pin-sentence-transformers
```

`main` stays deployable throughout. The demo link goes on a resume; a broken `main` is a broken demo at the worst possible moment.

### Commits

Short, imperative, present tense:

```
Add per-query min-max normalization to hybrid scoring
Fix hunk header parsing to retain function context
Record token_count and was_truncated on every chunk
Chore: pin sentence-transformers to 3.x
```

No paragraphs. A commit needing a paragraph is holding too much — split it.

Conventional Commits is overkill for a solo project. Be descriptive.

### Cadence

Commit at each meaningful unit — a function finished, a bug fixed, a section completed. Never accumulate twenty unrelated changes.

**Tag the milestones:**

```
git tag v0.1-vector-only     # end of Phase 3
git tag v0.2-hybrid          # end of Phase 6, weights locked
git tag v1.0                 # day 50
```

`v0.1` matters specifically: it is the last commit before hybrid retrieval exists, which makes the vector-only baseline reproducible when you need to show what hybrid actually bought.

---

## 4. Tooling

**Ruff** — linter and formatter in one. Replaces flake8, isort, and black with a single fast tool.

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]   # errors, pyflakes, imports, pyupgrade, bugbear
```

No bikeshedding on style. Ruff decides; you move on.

**pre-commit** — add around **week 3**, not day 1. Early on you are moving fast and changing shape constantly; hooks are friction. By week 3 the codebase is large enough that drift becomes a real cost.

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks: [{id: ruff, args: [--fix]}, {id: ruff-format}]
```

---

## 5. Type hints

**Annotate function signatures. Skip full `mypy` strictness.**

```python
def normalize(scores: dict[int, float]) -> dict[int, float]: ...
def parse_hunks(diff: str, pr_id: int) -> list[Hunk]: ...
```

Signatures give the reader and the editor everything they need. Chasing complete `mypy --strict` compliance on a solo 50-day build is overhead that buys little — the hard bugs here are logic bugs in scoring, not type errors.

Pydantic models carry the types for request and response bodies; they are validated at runtime anyway.

---

## 6. Constants and configuration

**No magic numbers anywhere in logic.** Every threshold from `03_retrieval_engine.md` lives in one module:

```python
# app/retrieval/constants.py
EMBEDDING_DIM       = 384
MAX_MODEL_TOKENS    = 256      # all-MiniLM-L6-v2 truncates silently past this

WEIGHT_VECTOR       = 0.50     # tuned on tune split, locked <date>
WEIGHT_FILE_OVERLAP = 0.30
WEIGHT_BM25         = 0.20

REASON_HIGH_VECTOR  = 0.70     # reason template rules 1 and 3
REASON_HIGH_BM25    = 0.70     # rule 4

CANDIDATE_TOP_N     = 50
RESULTS_RETURNED    = 3
```

The weight constants carry the date they were locked. When someone asks in an interview why the weights are what they are, the answer is in `01_evaluation_protocol.md` §13 — and the code points there.

**Configuration** is env-backed via `pydantic-settings`. `.env.example` lists every variable with a placeholder. `.env` is gitignored and never committed.

---

## 7. Comments

Code should be self-documenting. Comments explain **why**, not **what**.

```python
# Bad — restates the code
# Take the max score across chunks
score = max(chunk_scores)

# Good — explains the decision
# MAX not mean: the question is "did ANY part of this PR match ANY part of
# that one?" Averaging dilutes a strong specific match across a large PR's
# unrelated hunks. Compared against mean-of-top-3 during tuning —
# see 03_retrieval_engine.md §5.
score = max(chunk_scores)
```

```python
# Normalize per query, not globally: BM25 magnitude depends on the query's
# own terms, so global scaling would leak query characteristics into
# candidate scores and make ranks incomparable across queries.
```

```python
# Line numbers stripped, trailing context kept. "@@ -120,7 +120,9 @@" is
# digit noise that pollutes the embedding; "def jsonable_encoder(" is the
# enclosing function and among the best context in the hunk.
```

### When to comment

- Non-obvious decisions with a documented rationale (link the doc section)
- Workarounds for external behaviour (`# GitHub returns 403 on secondary rate limits, not 429`)
- `TODO` with owner and date: `# TODO(harshil, 2026-09): compare directory-level file overlap`

### When not to

- Restating the code
- Explanations that will go stale and never be updated
- Decorative banners

---

## 8. Error handling

**Never swallow an exception silently.** Log with context or let it propagate.

```python
# Bad
try:
    embed(hunk)
except Exception:
    pass

# Good
try:
    embed(hunk)
except Exception:
    log.exception("embedding failed", extra={"pr": pr_id, "file": path, "hunk": idx})
    continue   # indexing continues; one bad hunk must not kill a 3-hour run
```

Two rules from `04_architecture.md` restated because they are easy to violate under time pressure:

- **Indexing logs and continues.** A single failing PR never hard-fails the run.
- **Retrieval failure returns 503, not 500.** The Action treats it as retryable.

---

## 9. Performance defaults

Do these without thinking about them.

- **Batch embedding, always.** `model.encode(texts, batch_size=32)`. Encoding one hunk per call in a loop is roughly an order of magnitude slower and will turn indexing into an overnight job.
- **Model loads once**, in the FastAPI lifespan handler. Never per request, never at module import in a way that reloads.
- **`asyncpg` connection pool**, never per-request connections. Neon caps connections, and the pooled connection string exists for this reason.
- **Bulk insert chunks.** `executemany` or `COPY`, not row-by-row. Ten thousand individual inserts across a network to Neon is unusable.
- **Index every column used in `WHERE`, `ORDER BY`, or `GROUP BY`.** Querying without one is a bug, not a performance nit.
- **Fetch candidate metadata in one query.** The candidate set is ~150 PRs; N+1 lookups per candidate is the easiest way to make retrieval feel slow.
- **Do not add a vector index.** Settled in `02_data_models.md` §5 — exact search at this scale is milliseconds with perfect recall.

Everything else waits for a measurement. Premature optimization here costs days you have allocated elsewhere.

---

## 10. Module organization

- A module over ~300 lines is doing too much — split by responsibility, not by line count.
- One concept per module. `signals.py` computes signals; it does not normalize, rank, or format.
- **`app/` never imports from `eval/`.** Restated from `04_architecture.md` §3 because a single convenience import would create a path where deployed state influences a published number.
- `ingest/` is imported only by `scripts/`, never by `app/`.

---

## 11. Dependencies

**Pin everything.** `requirements.txt` with exact versions.

`torch`, `transformers`, and `sentence-transformers` churn frequently and break in ways that are slow to diagnose. A floating version means a rebuild in week 7 can silently change your embeddings — which invalidates every number you have published.

```
sentence-transformers==3.0.1
torch==2.3.1
asyncpg==0.29.0
fastapi==0.111.0
rank-bm25==0.2.2
```

**The embedding model version is part of your evaluation methodology.** Treat a model or library bump as requiring a full re-index and a re-run of the harness.

### CPU-only torch lives in the Dockerfile, not here

The deployed image installs torch from PyTorch's CPU index, cutting it from 1.6 GB to 433 MB. **That instruction cannot go in `requirements.txt`.**

`torch==2.3.1+cpu` wheels are published for Linux and Windows only. On macOS, PyPI's `torch==2.3.1` is *already* CPU-only, and pinning the `+cpu` local version would fail every local install.

So: `requirements.txt` pins `torch==2.3.1` and stays portable; the Dockerfile installs the CPU wheel first against the PyTorch index, and pip treats `2.3.1+cpu` as satisfying the pin (`04_architecture.md` §9). **The pin holds and the image shrinks** — the platform-specific instruction belongs where the platform is known.

---

## 12. Record keeping — three files, three purposes

Three files at the repository root. **They have different lifecycles, which is what keeps them from collapsing into each other.** Overlapping files are how all three end up abandoned.

| File | Lifecycle | Answers |
|---|---|---|
| `JOURNAL.md` | Append-only, dated | *What happened?* |
| `DECISIONS.md` | Append, with status | *Why is it this way?* |
| `HANDOFF.md` | **Overwritten** each close | *Where am I right now?* |

### `JOURNAL.md` — narrative

Append-only, dated. Two minutes, same day. Write when something breaks, a decision reverses, or a number surprises you.

```markdown
## 2026-08-14
Vector-only retrieval returned 3 translation PRs for query #16024.
Corpus filter was matching `lang-all` but not `lang-fr`. Changed to a
prefix match on `lang-`. Truncation rate measured at 18% of chunks —
higher than expected, worth naming in the README.
```

Not documentation for its own sake. It is the raw material for STAR interview answers, and the details are gone in six weeks if you do not write them down when they happen.

### `DECISIONS.md` — auditable ledger

Every decision that could later be second-guessed, logged **at commit time**.

```markdown
### D-P4-2 — CONFIRMED (2026-08-22)
Chunk→PR aggregation uses MAX, not mean-of-top-3.
Mean tested during Phase 6 tuning; MAX scored 4 pts higher on the
tune split. See 03_retrieval_engine.md §5.
```

Format: `D-P<phase>-<n>`, status `OPEN` or `CONFIRMED`, one paragraph of reasoning, and a link to the governing doc section where one exists.

**Audit it at the end of Phase 6**, before any number leaves the repository — check for missing entries, malformed headings, and stale `OPEN` markers that were resolved and never reconciled.

### `HANDOFF.md` — current state only

Overwritten at every session close, committed with the session's work. **Never history** — that is what the other two are for.

Full template in `11_workflow.md` §1. It exists so getting up to speed is `cat HANDOFF.md` rather than a search across dozens of conversations, and because a committed handoff is diffable: you can see what you carried forward and never closed.

---

## 13. Session discipline

Two rules that are conventions, not preferences.

**End the session at the commit.** `commit + DECISIONS.md entry + HANDOFF.md rewrite` is the last thing you do while you still have energy — not the thing you do while tired. Skipped log entries and bundled commits happen in the stretch after the code works and before you stop.

**Stop at the second transcription typo.** A cluster of one-token errors — a dropped character, wrong quote style, a plural where there should be none — is a fatigue signal, not a comprehension gap. The second one in a session ends the session. Commit what works, write the handoff, stop.

**Type logic, paste plumbing.** Typing code manually is a real learning practice for logic-heavy modules — `chunking.py`, `scoring.py`, `normalize.py`, `eval/score.py`. It teaches nothing on config files, Dockerfiles, SQL migrations, or CSS boilerplate, where it only adds transcription errors. Split by tier.

---

## 14. Checklist

- [ ] Ruff configured, line length 100
- [ ] pre-commit added by end of week 3
- [ ] Function signatures annotated; no `mypy --strict` chase
- [ ] All thresholds in `constants.py` with lock dates on weights
- [ ] `.env.example` complete; `.env` gitignored
- [ ] Raw vs normalized always explicit in variable names
- [ ] No silent `except: pass` anywhere
- [ ] Embedding batched; model loaded once in lifespan
- [ ] Connection pool, not per-request connections
- [ ] Chunks bulk-inserted
- [ ] `app/` imports nothing from `eval/` or `ingest/`
- [ ] All dependencies pinned
- [ ] CPU-only torch in the Dockerfile, never in `requirements.txt`
- [ ] `JOURNAL.md`, `DECISIONS.md`, and `HANDOFF.md` all created on day 1
- [ ] `HANDOFF.md` rewritten and committed at every session close
- [ ] `DECISIONS.md` audited at end of Phase 6
- [ ] Logic typed manually; plumbing pasted
- [ ] Milestone tags at v0.1, v0.2, v1.0
