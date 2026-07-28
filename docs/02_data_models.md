# PR Review Assistant — Data Models

**v1.0 — Locked July 2026**

Single store: **PostgreSQL with the `pgvector` extension**, hosted on Neon. PR metadata, chunk embeddings, and evaluation artifacts all live in one database.

Referenced by `01_evaluation_protocol.md` (§15 artifacts) and `03_retrieval_engine.md`.

---

## 1. Why one store

The original blueprint specified MongoDB for metadata and pgvector for embeddings. That was collapsed to Postgres alone.

**Rationale.** Postgres was already required for pgvector. Running a second database engine adds an operational surface, a second driver, and a consistency problem between PR records and their chunk vectors — in exchange for a document model that `JSONB` and array columns already provide. "Document structure fits PR data" is not a constraint; it is a preference that Postgres satisfies natively.

There is a secondary benefit that matters at query time: **file-overlap scoring and vector similarity execute in the same query**, against the same transactional snapshot. A split store would require joining across systems in application code.

---

## 2. Extension and conventions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

- All timestamps are `TIMESTAMPTZ`, stored UTC.
- Surrogate `BIGSERIAL` primary keys; GitHub identifiers are stored separately and constrained unique.
- Migrations are numbered plain SQL files (`migrations/001_init.sql`) applied in order. Alembic is unnecessary overhead for a solo project with a fixed schema.

---

## 3. `repos`

```sql
CREATE TABLE repos (
    id            BIGSERIAL PRIMARY KEY,
    github_id     BIGINT      NOT NULL UNIQUE,
    owner         TEXT        NOT NULL,
    name          TEXT        NOT NULL,
    full_name     TEXT        NOT NULL UNIQUE,
    status        TEXT        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','indexing','ready','failed')),
    total_prs     INTEGER     NOT NULL DEFAULT 0,
    indexed_prs   INTEGER     NOT NULL DEFAULT 0,
    indexed_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Why:** One row per indexed repository. `total_prs` and `indexed_prs` exist so indexing progress is queryable mid-run — GitHub ingestion takes hours and will be interrupted.

**Removed from the blueprint:** `webhook_id` and `last_synced_at`. The webhook receiver was cut in favour of the GitHub Action (see `04_architecture.md`), and incremental sync is deferred past day 50.

---

## 4. `pull_requests`

```sql
CREATE TABLE pull_requests (
    id                BIGSERIAL PRIMARY KEY,
    repo_id           BIGINT      NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    number            INTEGER     NOT NULL,
    github_id         BIGINT      NOT NULL,
    title             TEXT        NOT NULL,
    body              TEXT,
    author            TEXT        NOT NULL,
    author_type       TEXT        NOT NULL,       -- 'User' | 'Bot'
    outcome           TEXT        NOT NULL
                      CHECK (outcome IN ('merged','closed_unmerged','open')),
    labels            TEXT[]      NOT NULL DEFAULT '{}',
    files_changed     TEXT[]      NOT NULL DEFAULT '{}',
    additions         INTEGER     NOT NULL DEFAULT 0,
    deletions         INTEGER     NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL,
    merged_at         TIMESTAMPTZ,
    closed_at         TIMESTAMPTZ,
    in_corpus         BOOLEAN     NOT NULL DEFAULT TRUE,
    exclusion_reason  TEXT,
    raw               JSONB,
    UNIQUE (repo_id, number)
);

CREATE INDEX idx_pr_repo_created   ON pull_requests (repo_id, created_at DESC);
CREATE INDEX idx_pr_corpus         ON pull_requests (repo_id) WHERE in_corpus;
CREATE INDEX idx_pr_labels         ON pull_requests USING GIN (labels);
CREATE INDEX idx_pr_files          ON pull_requests USING GIN (files_changed);
```

### Design notes

**`outcome` is three values, not "rejected".** GitHub has no rejected state. `closed_unmerged` is the honest mapping — a PR closed without merging may have been superseded, abandoned, duplicated, or moved. The display layer surfaces it as *"closed without merging — worth checking why"*, never as *"rejected"*.

**`in_corpus` + `exclusion_reason` instead of deleting.** Filtered PRs (bots, `lang-*`, `docs`, `release`, housekeeping — see `01_evaluation_protocol.md` §2) are **marked, not removed**.

Three reasons, and this is the most consequential decision in the schema:
1. GitHub's API is rate-limited to 5,000 requests/hour. Re-fetching after a filter change costs hours.
2. The filter itself becomes auditable — `SELECT exclusion_reason, count(*) GROUP BY 1` proves what was excluded and lets you publish those counts in the README.
3. Filter criteria will change during development. Reversing a decision must not require re-ingestion.

**Arrays, not JSONB, for `labels` and `files_changed`.** Both are queried: labels drive corpus filtering, `files_changed` drives Jaccard overlap scoring. `TEXT[]` with GIN indexes supports containment and overlap operators directly. `JSONB` is reserved for `raw` — fields kept for future use but never filtered on.

**No `diff_raw` column.** The blueprint stored the full raw diff per PR. Removed.

The `chunks` table already contains every hunk of every diff; `diff_raw` would duplicate that content entirely. Beyond redundancy, diff size has extreme variance — a refactor touching 40 files can exceed 500 KB — which makes storage unpredictable against a 0.5 GB quota. Anything needing the original diff can reconstruct it by ordering that PR's chunks.

---

## 5. `chunks`

```sql
CREATE TABLE chunks (
    id             BIGSERIAL PRIMARY KEY,
    pr_id          BIGINT      NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
    repo_id        BIGINT      NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    file_path      TEXT        NOT NULL,
    hunk_index     INTEGER     NOT NULL,
    content        TEXT        NOT NULL,
    token_count    INTEGER     NOT NULL,
    was_truncated  BOOLEAN     NOT NULL DEFAULT FALSE,
    additions      INTEGER     NOT NULL DEFAULT 0,
    deletions      INTEGER     NOT NULL DEFAULT 0,
    embedding      VECTOR(384),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pr_id, file_path, hunk_index)
);

CREATE INDEX idx_chunks_pr   ON chunks (pr_id);
CREATE INDEX idx_chunks_repo ON chunks (repo_id);
```

### Design notes

**`VECTOR(384)`** matches `all-MiniLM-L6-v2` output. The dimension is fixed by the model; changing models requires a migration and a full re-embed.

**`token_count` and `was_truncated` are the most important columns here.** `all-MiniLM-L6-v2` silently truncates input beyond 256 tokens — a large `@@` block is simply cut off, with no error. Recording both makes the failure measurable:

```sql
SELECT count(*) FILTER (WHERE was_truncated) * 100.0 / count(*) FROM chunks;
```

That percentage belongs in the README. A limitation you have quantified is a strength; one you have not noticed is a defect an interviewer will find first.

**`repo_id` is denormalized** from `pull_requests`. Every retrieval query filters by repository before scanning vectors; the join would run on every request for no benefit.

**`UNIQUE (pr_id, file_path, hunk_index)`** makes re-indexing idempotent. Indexing will be interrupted and restarted.

### Vector index: deliberately none in v1

No IVFFlat or HNSW index is created.

**Rationale.** At the expected corpus size — roughly 10,000 chunks — pgvector's exact nearest-neighbour scan runs in single-digit milliseconds and returns **perfect recall**. ANN indexes trade recall for speed at a scale this project does not reach. Adding one would degrade result quality to solve a problem that does not exist.

**Documented scale path:** beyond ~100,000 chunks, add HNSW (`vector_cosine_ops`), accept approximate recall, and re-run the evaluation harness to measure what that approximation costs. This is the correct answer to *"what happens at 10,000 PRs?"* — the honest bottleneck is embedding throughput at ingest, not query latency.

**Distance operator:** cosine (`<=>`). Cosine measures direction rather than magnitude, which is what semantic similarity means — and it is magnitude-invariant on its own, independent of whether the stored vectors are normalized (03_retrieval_engine.md §3). Euclidean distance would penalize longer diffs for producing larger-magnitude vectors even when semantically identical to shorter ones.

---

## 6. `eval_queries`

```sql
CREATE TABLE eval_queries (
    id          BIGSERIAL PRIMARY KEY,
    pr_id       BIGINT      NOT NULL UNIQUE REFERENCES pull_requests(id),
    subsystem   TEXT        NOT NULL,
    split       TEXT        NOT NULL CHECK (split IN ('tune','holdout')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Why:** The 20 evaluation queries and their tune/holdout assignment. `subsystem` enforces the stratification requirement in `01_evaluation_protocol.md` §8 — a single `GROUP BY subsystem` proves coverage spans at least six areas rather than clustering in three.

The split is stored in the database, not decided at script runtime, so it cannot drift between runs. Reproducibility depends on this being fixed once.

---

## 7. `judgments`

```sql
CREATE TABLE judgments (
    id               BIGSERIAL PRIMARY KEY,
    query_pr_id      BIGINT      NOT NULL REFERENCES pull_requests(id),
    candidate_pr_id  BIGINT      NOT NULL REFERENCES pull_requests(id),
    grade            SMALLINT    NOT NULL CHECK (grade IN (0,1,2)),
    reason           TEXT,
    round            SMALLINT    NOT NULL DEFAULT 1 CHECK (round IN (1,2)),
    batch            SMALLINT    NOT NULL,
    seconds_spent    INTEGER,
    self_authored    BOOLEAN     NOT NULL DEFAULT FALSE,
    labeled_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (query_pr_id, candidate_pr_id, round),
    CHECK (grade = 0 OR reason IS NOT NULL)
);

CREATE INDEX idx_judgments_query ON judgments (query_pr_id, round);
```

### Design notes

**`CHECK (grade = 0 OR reason IS NOT NULL)` enforces the rubric in the schema.** The protocol requires a written reason for every grade 1 and 2 (§10). A constraint makes that structurally impossible to skip during a four-hour labeling session — which is exactly when discipline fails.

**`round` supports the self-agreement re-test.** Round 1 is the original judgment; round 2 is the blind re-label a week later. Because the unique constraint includes `round`, both coexist and quadratic weighted kappa is a single join:

```sql
SELECT a.grade, b.grade
FROM judgments a
JOIN judgments b USING (query_pr_id, candidate_pr_id)
WHERE a.round = 1 AND b.round = 2;
```

Overwriting round 1 would destroy the ability to measure labeling reliability at all.

**`seconds_spent`** tracks adherence to the ~45-second time box. A session where judgments drift to three minutes each indicates fatigue and inconsistent calibration — worth knowing before trusting the batch.

**No `system_rank` column.** The blueprint stored where the system ranked each candidate. Deliberately omitted: judgments must be **blind**, and a rank column in the labeling table invites anchoring. Rank is recoverable at scoring time by re-running retrieval.

---

## 8. `similarity_results`

```sql
CREATE TABLE similarity_results (
    id            BIGSERIAL PRIMARY KEY,
    query_pr_id   BIGINT      NOT NULL REFERENCES pull_requests(id),
    repo_id       BIGINT      NOT NULL REFERENCES repos(id),
    results       JSONB       NOT NULL,
    weights       JSONB       NOT NULL,
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    posted        BOOLEAN     NOT NULL DEFAULT FALSE,
    posted_at     TIMESTAMPTZ,
    comment_url   TEXT
);

CREATE INDEX idx_simres_query ON similarity_results (query_pr_id, computed_at DESC);
```

`results` shape:

```json
[
  {
    "pr_id": 15992,
    "pr_number": 15992,
    "title": "fix: pass include/exclude/by_alias params to jsonable_encoder",
    "outcome": "closed_unmerged",
    "final_score": 0.71,
    "vector_score": 0.68,
    "file_score": 1.0,
    "bm25_score": 0.42,
    "reason": "Both modify jsonable_encoder parameter handling"
  }
]
```

**Why JSONB here and not a child table:** results are written once and read whole. Normalizing into `similarity_result_items` would add a join to satisfy a shape that is never queried by individual field.

**`weights` is stored per result.** Posted comments are historical artifacts; knowing which weight configuration produced a given comment is essential when the scores are later re-tuned. Without it, a comment posted in week 6 is unexplainable in week 8.

---

## 9. Storage budget

Neon's free tier allows **0.5 GB per project**. Estimated usage at full corpus:

| Table | Estimate |
|---|---|
| `chunks.embedding` | 10,000 × 1.6 KB ≈ **16 MB** |
| `chunks.content` | 10,000 × ~1.5 KB ≈ **15 MB** |
| `pull_requests` (incl. `raw`) | 1,000 × ~5 KB ≈ **5 MB** |
| `judgments`, `eval_queries` | < 1 MB |
| Indexes | ≈ **10 MB** |
| **Total** | **≈ 50 MB — about 10% of quota** |

**These figures are FastAPI-derived and are not re-estimated here.** The corpus
is now `processing/p5.js` (`01_evaluation_protocol.md` §2), roughly 4,175 closed
PRs against FastAPI's ~5,964 — the same order of magnitude, so the table's
conclusion (≈10% of quota) is not at risk. The chunk count is the figure that
could move, since it depends on diff size distribution rather than PR count,
and that is unknown until the Phase 2 ingest run. Re-measure with the query
below after the first full index rather than revising the estimate now.

Comfortable headroom. Two things would break this: storing `diff_raw` (§4), or indexing multiple large repositories. Both are avoided; multi-repo support is deferred past day 50 (`00_problem_statement.md` §6).

**FastAPI is cached, not indexed.** The Day-4 spike's raw diffs stay in `.cache/`
so the recorded separation figures remain reproducible, but no FastAPI PR enters
`pull_requests`. Cached is not indexed, and the distinction is what keeps the
multi-repo non-goal intact.

Monitor with:

```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
```

---

## 10. Entity relationships

```
repos 1──n pull_requests 1──n chunks
                │
                ├──1 eval_queries        (20 rows — the evaluation query set)
                ├──n judgments           (as query_pr_id — ~300 rows)
                ├──n judgments           (as candidate_pr_id)
                └──n similarity_results  (as query_pr_id)
```

`ON DELETE CASCADE` runs from `repos` down through `chunks`, so dropping a repository cleans up entirely. Evaluation tables intentionally do **not** cascade — judgments are irreplaceable hand-labeled work and must never be deleted by a re-index.

---

## 11. Checklist

- [ ] `vector` extension enabled on Neon
- [ ] Migrations numbered and applied in order
- [ ] GIN indexes on `labels` and `files_changed`
- [ ] No ANN index on `chunks.embedding` (exact search, v1)
- [ ] `UNIQUE (pr_id, file_path, hunk_index)` present — re-indexing is idempotent
- [ ] Reason-required CHECK on `judgments` present
- [ ] Evaluation tables excluded from cascade deletes
- [ ] Database size verified under 250 MB after full index
