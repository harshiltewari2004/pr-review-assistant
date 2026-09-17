"""Shared test fixtures. 07 §7 — local Postgres only, never Neon."""

from __future__ import annotations

from collections.abc import AsyncIterator

import asyncpg
import pytest_asyncio

from ingest.db import connect


@pytest_asyncio.fixture
async def db() -> AsyncIterator[asyncpg.Connection]:
    """Local Postgres connection in a transaction that always rolls back.

    Goes through ingest.db.connect() rather than asyncpg.connect() so the
    test sees production's codec registration. D-P2-25 permits this import:
    only app/ -> ingest/ and app/ -> eval/ are prohibited, not tests/ -> ingest/.

    07 §7 pins target to local. The local database holds the real 3,196-PR
    corpus; a test that committed fixture rows would leave them there and
    every later measurement would silently include them. Rollback lives in
    finally so a failing assertion cleans up too.
    """
    async with connect("local") as conn:
        tx = conn.transaction()
        await tx.start()
        try:
            yield conn
        finally:
            await tx.rollback()
