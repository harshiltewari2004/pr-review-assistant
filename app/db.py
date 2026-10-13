"""asyncpg pool for the service (04 §9). D-P7-2.

Separate from ingest/db.py because app/ never imports ingest/ (04 §3); the
codecs match ingest's exactly, so vectors decode identically.
statement_cache_size=0: Neon's POOLED endpoint is PgBouncer in transaction
mode, which breaks asyncpg's prepared-statement cache (D-P3-2). Harmless locally.
"""

from __future__ import annotations

import json

import asyncpg
from pgvector.asyncpg import register_vector

POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 4


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await register_vector(conn)


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        dsn,
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
        statement_cache_size=0,
        init=_init_connection,
    )
