# PR Review Assistant — Retrieval Engine

**v1.0 — Locked July 2026**

The core technical component. Defines how a diff becomes vectors, how three signals are computed and combined, and how results become human-readable reasons.

Depends on `02_data_models.md`. Measured by `01_evaluation_protocol.md`.

---

## 1. Why hybrid retrieval

Pure vector search over code is mediocre. Each signal catches a different kind of similarity:

| Signal | Catches | Misses |
|---|---|---|
| **Vector** | Semantic similarity — two diffs doing the same thing in different words | Structural relationships when phrasing diverges |
| **File overlap** | Structural similarity — two PRs touching the same module are related regardless of wording | Cross-file relationships; over-fires on frequently-touched files |
| **BM25** | Exact terminology — function names, variable names, error strings | Paraphrase; anything not lexically shared |

The combination outperforms any single signal. Whether that claim holds is **measured**, not asserted — the evaluation harness scores all three individually alongside the hybrid, and those numbers are published.

---

## 2. Hunk-level chunking

### Granularity decision

| Level | Problem |
|---|---|
| Full diff | A PR touching 12 files becomes one averaged vector representing nothing well |
| Line level | A single line has no meaning without surrounding code |
| **Hunk (`@@` block)** | **Chosen.** A coherent unit of change with enough surrounding context to embed meaningfully |

### Parsing

```
1. Split raw diff on `diff --git` → per-file blocks
2. Extract file path from the `+++ b/<path>` line
3. Skip the block if the file is excluded (see below)
4. Split the block body on `@@` markers → hunks
5. Emit one chunk per hunk, with file_path and hunk_index
```

### File-level exclusions

Chunks are **not** created for:

- Binary files (no textual hunks)
- Deleted files (`+++ /dev/null`) — the content is gone; there is nothing to match against
- Non-source extensions: `.md`, `.txt`, `.rst`, `.po`, `.lock`, `.svg`
- Lockfiles and locale payloads: `package-lock.json`, and `translations/*/translation.json`. **The exclusion is on the payloads, not the directory** — `translations/dev.js` and `translations/index.js` are the i18next loader and are ordinary source.
- Generated or vendored paths

**Note:** this is a *second* filter, distinct from the corpus filter in `01_evaluation_protocol.md` §2. A PR can pass the corpus filter (it is a genuine code change) while individual files inside it are skipped. A bug fix that also updates a changelog should be indexed on its code hunks only.

### Hunk header handling

A hunk header looks like:

```
@@ -120,7 +120,9 @@ def jsonable_encoder(
```

**Line numbers are stripped. The trailing context is kept.**

`-120,7 +120,9` is pure noise — line numbers carry no semantic content and would pollute the embedding with digit tokens. But `def jsonable_encoder(` is the enclosing function, which is among the most useful signal in the entire hunk. Discarding the whole header, as a naive split would, throws away the best context available.

### `+`/`-` prefixes are retained

They carry real signal: a line removed and a line added mean different things. The model treats them as tokens; that is acceptable.

### Edge cases

| Case | Handling |
|---|---|
| Empty diff (no file changes) | PR indexed with zero chunks; vector signal contributes nothing |
| Renamed file, no content change | Skipped — no hunks |
| Hunk exceeding 256 tokens | Embedded truncated, `was_truncated = TRUE` (see §3) |
| Single-line hunk | Kept — short but valid |

---

## 3. Embedding

**Model:** `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions, run locally.

**Why this model.** No external API dependency, no per-token cost, fast on CPU, and — critically — **the evaluation results are fully reproducible** because the model never changes underneath you. An API-backed embedding model would make the published numbers unverifiable the moment the provider updates.

### Known limitation, stated openly

This is a **natural-language sentence model applied to code diffs**. It was trained on short English text, not on source code. A code-aware embedder (CodeBERT, GraphCodeBERT, or a code-tuned sentence model) would raise the ceiling on the vector signal.

This is a deliberate cost/latency/reproducibility tradeoff, not an oversight. It is stated in the README and is the correct answer when an interviewer asks about model choice. **Documented upgrade path:** swap the model, re-embed, re-run the evaluation harness, and report the delta — the harness exists precisely to make that measurable.

### Truncation

`all-MiniLM-L6-v2` silently truncates input beyond **256 tokens**. A 40-line hunk exceeds this easily, and the model raises no error.

**Handling:**
1. Tokenize before encoding; record `token_count`
2. Set `was_truncated = TRUE` when `token_count > 256`
3. Log a warning at ingest
4. Publish the corpus-wide truncation rate in the README

A quantified limitation is a strength. An unnoticed one is a defect an interviewer finds first.

### Encoding parameters

```python
model.encode(
    texts,
    normalize_embeddings=True,   # unit vectors — cosine reduces to dot product
    batch_size=32,               # throughput during bulk indexing
    show_progress_bar=False,
)
```

`normalize_embeddings=True` is not what makes `<=>` cosine — pgvector's `<=>` divides by both norms itself, so it returns identical distances on unnormalized vectors and identical rankings. What normalization buys is **agreement outside Postgres.** On unit vectors, `1 - (a <=> b)` equals a plain dot product, so a similarity computed in numpy, in a spike script, or via pgvector's `<#>` inner-product operator ranks the same way `<=>` does. Unnormalized, those disagree — and the disagreement is silent, which puts it in `11_workflow.md` §5's expensive category. The inline comment in the block above states the actual reason correctly.

---

## 4. Candidate set construction

All three signals must be normalized **over the same candidate set** (§8). The set is therefore built before any scoring.

```
1. Apply hard filters:
     repo_id = <repo>
     in_corpus = TRUE
     created_at < query.created_at     ← temporal filter, mandatory
     id <> query.id
2. Take top 50 by raw vector score
3. Take top 50 by raw BM25 score
4. Take every PR with file overlap > 0 (capped at 100)
5. Union and deduplicate → candidate set C (typically 100–150 PRs)
6. Compute all three raw signals for every member of C
```

**The temporal filter is enforced here, in code.** The product surfaces *past* PRs; permitting a later PR to be retrieved would credit the system for information it could not have had. See `01_evaluation_protocol.md` §5.

**Why a union rather than vector-only candidates:** a PR with perfect file overlap but weak embedding similarity must be able to enter the ranking. Seeding the candidate set from one signal would make the other two unable to rescue anything that signal missed — which defeats the purpose of hybrid retrieval.

---

## 5. Signal 1 — Vector similarity

The query PR's chunks are embedded, then matched against candidate chunks.

```sql
SELECT c.pr_id,
       MAX(1 - (c.embedding <=> $1::vector)) AS vector_score
FROM chunks c
JOIN pull_requests p ON p.id = c.pr_id
WHERE c.repo_id  = $2
  AND p.in_corpus
  AND p.created_at < $3
  AND p.id <> $4
GROUP BY c.pr_id
ORDER BY vector_score DESC
LIMIT 50;
```

Run once per query chunk; take the maximum across all query chunks for each candidate PR.

**Cosine, not Euclidean.** Cosine measures the angle between vectors, ignoring magnitude. Two semantically similar texts point in the same direction regardless of length. Euclidean distance would penalize longer diffs for producing larger-magnitude vectors even when semantically identical to shorter ones.

### Chunk → PR aggregation

**v1 uses `MAX`** across all (query chunk, candidate chunk) pairs.

**Rationale:** the question being asked is *"did **any** part of this new PR strongly match **any** part of a past PR?"* Averaging would dilute a strong, specific match across a large PR's unrelated hunks.

**Known weakness, and how it is handled.** `MAX` is noisy — one coincidental hunk match inflates an entire PR's score. **Mean-of-top-3** is more robust.

Rather than assert which is better, **both are implemented and compared during weight tuning** on the tune split. The winner is locked and the comparison is published. This is a measurable question, not a matter of opinion.

---

## 6. Signal 2 — File path overlap

Jaccard similarity between the two PRs' `files_changed` sets:

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

Naturally bounded in `[0, 1]`.

**Computed in Python, not SQL.** The candidate set is already reduced to ~150 PRs; expressing set intersection over `TEXT[]` in SQL is awkward and buys nothing at this size.

**Exact path matching in v1.** Directory-level overlap (crediting `fastapi/routing.py` against `fastapi/dependencies/utils.py` for a shared prefix) is a documented variant to evaluate during tuning, not a v1 default. Exact matching is stricter and easier to reason about.

**Known bias:** frequently-touched files (`fastapi/encoders.py`, `fastapi/routing.py`) produce overlap between genuinely unrelated PRs. This is precisely why the evaluation rubric forbids "same file" alone from earning a grade 2 (`01_evaluation_protocol.md` §6, rule 1) — otherwise this signal would score perfectly by construction and the evaluation would be circular.

---

## 7. Signal 3 — BM25

**Library:** `rank-bm25` (`BM25Okapi`).

### Document construction

Per PR: `title` + `body` + basenames of `files_changed`.

Including file basenames matters. Titles and descriptions alone are thin — many PR bodies are a sentence. Adding `encoders.py`, `routing.py` gives BM25 the identifier vocabulary it is best at matching.

### Tokenization

```
1. Lowercase
2. Split on non-alphanumeric
3. Additionally split snake_case and camelCase
4. Keep BOTH the whole identifier and its sub-tokens
```

Step 4 is the important one. `jsonable_encoder` is retained *and* emits `jsonable`, `encoder`. A PR whose title says "encoder" then partially matches one that says `jsonable_encoder`, while an exact reference to the full identifier still scores highest. Losing either behaviour loses real matches.

### Persistence

`rank-bm25` holds its corpus **in memory and has no on-disk index.**

- The corpus is loaded from Postgres at service startup and the index built once. At ~1,000 PRs this takes well under a second.
- Newly indexed PRs require a rebuild. Acceptable: indexing is a batch operation, not continuous.

**Considered and rejected:** Postgres `tsvector` + `ts_rank_cd` would be persistent and keep everything in one store, but it is not true BM25 and its ranking behaviour is harder to reason about and explain. `rank-bm25` is locked for v1; the Postgres approach is the documented path if in-memory state becomes a constraint.

---

## 8. Per-query normalization

**This is the single most important correction to the original design.**

### The problem

The blueprint specified:

```
final = 0.5 × vector + 0.3 × file_overlap + 0.2 × bm25
```

This assumes all three live on the same scale. They do not:

| Signal | Range |
|---|---|
| Vector (cosine, normalized) | ≈ `[0, 1]` |
| File overlap (Jaccard) | `[0, 1]` exactly |
| **BM25** | **Unbounded** — depends on term frequency, corpus size, document lengths. Observed values range from 0 to 15+ |

Adding a raw BM25 score to a cosine score is arithmetically meaningless. The `0.2` weight is fiction until the scales match — and because BM25's magnitude dwarfs the others, it silently dominates the ranking while appearing to be the smallest weight.

### The fix

**Min-max normalize each signal independently, per query, across the candidate set:**

```python
def normalize(scores: dict[int, float]) -> dict[int, float]:
    lo, hi = min(scores.values()), max(scores.values())
    if hi == lo:
        # No discriminative information from this signal for this query
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}
```

Applied to all three signals over the same candidate set `C`, **before** the weighted sum.

### Why per-query, not global

BM25 magnitudes depend on the query's own terms. A query PR containing rare identifiers produces far higher raw scores than one using common vocabulary. Global normalization would let *query characteristics* leak into candidate scores, making ranks incomparable between queries.

Signals are only ever compared **within** a single ranking decision. Normalizing at exactly that scope is correct.

### Why min-max, not z-score

Min-max bounds output to `[0, 1]`, which is what the weighted sum assumes. Z-score produces negative values and unbounded tails, breaking the interpretation of the weights entirely.

Z-score is a documented variant to test during tuning.

### Degenerate case

When `max == min` — every candidate scores identically on a signal — that signal is assigned `0.0` for all candidates. It carries no discriminative information for this query, and forcing an arbitrary value would inject noise.

---

## 9. Final score

```
final = w_v · vector_norm + w_f · file_norm + w_b · bm25_norm
```

**Starting weights:** `w_v = 0.5`, `w_f = 0.3`, `w_b = 0.2`.

These are a **starting point only**. Final weights are tuned on the tune split per `01_evaluation_protocol.md` §13, locked before the holdout set is examined, and published in the README with the reasoning behind them.

Constraint: weights sum to 1.0, keeping `final` bounded in `[0, 1]` and directly interpretable.

Top 3 by `final` are returned.

---

## 10. Reason generation

**Template-based, not LLM-generated.**

An LLM would reintroduce the external API dependency and per-call cost that the local embedding model exists to avoid, and would make comment output non-deterministic — which undermines reproducibility. Deferred past day 50.

### Rules — first match wins

| Priority | Condition | Template |
|---|---|---|
| 1 | Shared file **and** `vector_norm > 0.7` | `Both modify {shared_file} with a similar change pattern` |
| 2 | Shared file, lower vector | `Also changes {shared_file}` |
| 3 | `vector_norm > 0.7`, no shared file | `Similar change pattern in {their_top_file}` |
| 4 | `bm25_norm > 0.7` | `Shares terminology: {top_2_matched_terms}` |
| 5 | Fallback | `Related change in {top_level_directory}` |

Thresholds are named constants in one module, not scattered literals.

### Outcome suffix

Appended when `outcome = 'closed_unmerged'`:

> ` — closed without merging, worth checking why`

**Never "rejected."** GitHub has no rejected state; a closed-unmerged PR may have been superseded, abandoned, duplicated, or moved to another branch. Asserting rejection would produce confident false positives on the highest-value signal in the entire system. See `02_data_models.md` §4.

---

## 11. Full pipeline

```
New PR opened
  ↓
Fetch diff via GitHub API
  ↓
Chunk into hunks           (§2)  — file exclusions, header handling
  ↓
Embed each hunk            (§3)  — record token_count, was_truncated
  ↓
Build candidate set        (§4)  — temporal filter enforced here
  ↓
Compute raw signals        (§5,6,7)
  ↓
Normalize per query        (§8)  ← the correction
  ↓
Weighted sum → rank        (§9)
  ↓
Top 3 → reason strings     (§10)
  ↓
Cache to similarity_results, post comment
```

---

## 12. Decisions removed from the blueprint

| Removed | Reason |
|---|---|
| Raw weighted sum without normalization | Arithmetically invalid; BM25 is unbounded (§8) |
| LLM-generated reason strings | Reintroduces API dependency; non-deterministic output (§10) |
| "Rejected" PR label | GitHub has no such state; produces false positives (§10) |
| Full-diff and line-level chunking | Loses granularity and context respectively (§2) |
| Asserting `MAX` aggregation is correct | Made a measurable tuning question instead (§5) |

---

## 13. Checklist

- [ ] Hunk headers strip line numbers, retain function context
- [ ] Non-source and deleted files excluded at chunk level
- [ ] `normalize_embeddings=True` set
- [ ] `token_count` and `was_truncated` recorded for every chunk
- [ ] Temporal filter enforced in candidate-set construction
- [ ] Candidate set is a union across all three signals
- [ ] All three signals normalized over the **same** candidate set
- [ ] Degenerate `max == min` case returns 0.0
- [ ] Weights sum to 1.0
- [ ] `MAX` vs mean-of-top-3 compared during tuning, result published
- [ ] Reason thresholds are named constants
- [ ] Outcome suffix reads "closed without merging", never "rejected"
