-- 001_init.sql
-- Schema per 02_data_models.md. Applied to BOTH local Postgres and Neon.
-- Single store: Postgres + pgvector (see §1 for why not MongoDB + pgvector).

CREATE EXTENSION IF NOT EXISTS vector;

-- §3 -------------------------------------------------------------------------
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

-- §4 -------------------------------------------------------------------------
-- outcome is three values, never "rejected" — GitHub has no rejected state.
-- in_corpus + exclusion_reason: filtered PRs are MARKED, not deleted.
-- No diff_raw column: chunks are the source of truth for diff content.
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

-- §5 -------------------------------------------------------------------------
-- token_count / was_truncated: all-MiniLM-L6-v2 truncates silently past 256.
-- UNIQUE (pr_id, file_path, hunk_index) makes re-indexing idempotent.
-- NO ANN index on embedding in v1 — exact search at ~10k chunks is
-- milliseconds with perfect recall.
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

-- §6 -------------------------------------------------------------------------
-- subsystem enforces the stratification requirement (01 §8).
-- split stored in the DB, not decided at runtime, so it cannot drift.
CREATE TABLE eval_queries (
    id          BIGSERIAL PRIMARY KEY,
    pr_id       BIGINT      NOT NULL UNIQUE REFERENCES pull_requests(id),
    subsystem   TEXT        NOT NULL,
    split       TEXT        NOT NULL CHECK (split IN ('tune','holdout')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- §7 -------------------------------------------------------------------------
-- CHECK enforces the rubric: reason required for every grade 1 and 2 (01 §10).
-- round supports the self-agreement re-test; round 1 is never overwritten.
-- No system_rank column — judgments must be blind.
CREATE TABLE judgments (
    id               BIGSERIAL PRIMARY KEY,
    query_pr_id      BIGINT      NOT NULL REFERENCES pull_requests(id),
    candidate_pr_id  BIGINT      NOT NULL REFERENCES pull_requests(id),
    grade            SMALLINT    NOT NULL CHECK (grade IN (0,1,2)),
    reason           TEXT,
    round            SMALLINT    NOT NULL DEFAULT 1 CHECK (round IN (1,2)),
    batch            SMALLINT    NOT NULL,
    seconds_spent    INTEGER,
    labeled_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (query_pr_id, candidate_pr_id, round),
    CHECK (grade = 0 OR reason IS NOT NULL)
);

CREATE INDEX idx_judgments_query ON judgments (query_pr_id, round);

-- §8 -------------------------------------------------------------------------
-- weights stored per result: a comment posted in week 6 must remain
-- explainable in week 8 after re-tuning.
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
