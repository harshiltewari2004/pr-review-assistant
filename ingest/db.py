"""asyncpg connection for the local indexing pipeline (04 §5).

Separate from app/db.py by design. Scripts use the DIRECT Neon endpoint —
the pooled endpoint exists for the Cloud Run instance churn described in
04 §9 and is Phase 7's problem (D-P3-2). A long single-connection batch
write has nothing to gain from a pooler and something to lose: PgBouncer
in transaction mode breaks prepared-statement caching, which asyncpg
uses by default.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager

import asyncpg

LOCAL_DSN = "postgresql://postgres:dev@localhost/prreview"


def resolve_dsn(target: str) -> str:
    """target is 'local' or 'neon'. No default — the destination is always explicit."""
    if target == "local":
        return LOCAL_DSN
    if target == "neon":
        dsn = os.environ.get("DATABASE_URL_DIRECT")
        if not dsn:
            raise SystemExit("DATABASE_URL_DIRECT unset — see 08 §3")
        return dsn
    raise SystemExit(f"unknown target {target!r}; expected 'local' or 'neon'")


@asynccontextmanager
async def connect(target: str):
    conn = await asyncpg.connect(resolve_dsn(target))
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.dumps,
        schema="pg_catalog",
    )
    try:
        yield conn
    finally:
        await conn.close()


UPSERT_REPO = """
INSERT INTO repos (github_id, owner, name, full_name, status, total_prs)
VALUES ($1, $2, $3, $4, 'indexing', $5)
ON CONFLICT (github_id) DO UPDATE
SET status = 'indexing', total_prs = EXCLUDED.total_prs
RETURNING id
"""

UPSERT_PR = """
INSERT INTO pull_requests (
    repo_id, number, github_id, title, body, author, author_type, outcome,
    labels, files_changed, additions, deletions, created_at, merged_at,
    closed_at, in_corpus, exclusion_reason, raw
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
    $17, $18
)
ON CONFLICT (repo_id, number) DO UPDATE SET
    title = EXCLUDED.title,
    body = EXCLUDED.body,
    outcome = EXCLUDED.outcome,
    labels = EXCLUDED.labels,
    files_changed = EXCLUDED.files_changed,
    additions = EXCLUDED.additions,
    deletions = EXCLUDED.deletions,
    merged_at = EXCLUDED.merged_at,
    closed_at = EXCLUDED.closed_at,
    in_corpus = EXCLUDED.in_corpus,
    exclusion_reason = EXCLUDED.exclusion_reason,
    raw = EXCLUDED.raw
"""
