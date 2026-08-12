"""asyncpg connection for the local indexing pipeline (04 §5).

Separate from app/db.py by design. Scripts use the DIRECT Neon endpoint —
the pooled endpoint exists for the Cloud Run instance churn described in
04 §9 and is Phase 7's problem (D-P3-2). A long single-connection batch
write has nothing to gain from a pooler and something to lose: PgBouncer
in transaction mode breaks prepared-statement caching, which asyncpg
uses by default.
"""

from __future__ import annotations

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
    try:
        yield conn
    finally:
        await conn.close()
