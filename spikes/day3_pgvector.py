"""Day 3 spike — pgvector round-trip through asyncpg, local + Neon.

Throwaway. Proves the driver-level path the day-1 psql check did not cover.
Writes into the real chunks table inside a transaction that is rolled back,
so both databases are left untouched.

Run from repo root:  python spikes/day3_pgvector.py
"""

import asyncio
import os
import sys

import asyncpg
import numpy as np

sys.path.insert(0, os.getcwd())
from app.retrieval.constants import EMBEDDING_DIM  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("! python-dotenv not installed; relying on exported env vars")


def build_vectors() -> dict[str, np.ndarray]:
    """Four deterministic unit vectors with known pairwise cosines."""
    rng = np.random.default_rng(42)
    a = rng.normal(size=EMBEDDING_DIM)
    a /= np.linalg.norm(a)

    b = rng.normal(size=EMBEDDING_DIM)
    b -= (b @ a) * a  # Gram-Schmidt: strip the component along a
    b /= np.linalg.norm(b)

    return {"identical": a, "double_magnitude": 2 * a, "orthogonal": b, "opposite": -a}


def to_literal(v: np.ndarray) -> str:
    """pgvector's text input format. Full float repr — let the server truncate."""
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


async def check_schema(conn: asyncpg.Connection) -> None:
    ext = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname='vector'")
    tables = await conn.fetchval(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
    )
    # atttypmod on a vector column encodes the declared dimension.
    dims = await conn.fetchval(
        """SELECT atttypmod FROM pg_attribute
           WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"""
    )
    print(f"  pgvector      : {ext}")
    print(f"  public tables : {tables}")
    print(f"  chunks.embedding dims : {dims}")
    assert ext is not None, "vector extension missing"
    assert tables == 6, f"expected 6 tables, found {tables}"
    assert dims == EMBEDDING_DIM, f"column is vector({dims}), constants say {EMBEDDING_DIM}"


async def round_trip(conn: asyncpg.Connection, vecs: dict[str, np.ndarray]) -> None:
    query_vec = vecs["identical"]
    tr = conn.transaction()
    await tr.start()
    try:
        repo_id = await conn.fetchval(
            """INSERT INTO repos (github_id, owner, name, full_name)
               VALUES (-1, 'spike', 'spike', 'spike/day3') RETURNING id"""
        )
        pr_id = await conn.fetchval(
            """INSERT INTO pull_requests
                 (repo_id, number, github_id, title, author, author_type, outcome, created_at)
               VALUES ($1, -1, -1, 'spike', 'spike', 'User', 'open', now())
               RETURNING id""",
            repo_id,
        )

        for idx, (label, v) in enumerate(vecs.items()):
            await conn.execute(
                """INSERT INTO chunks
                     (pr_id, repo_id, file_path, hunk_index, content, token_count, embedding)
                   VALUES ($1, $2, $3, $4, $5, 0, $6::vector)""",
                pr_id,
                repo_id,
                f"spike/{label}.py",
                idx,
                label,
                to_literal(v),
            )

        rows = await conn.fetch(
            """SELECT content AS label,
                      1 - (embedding <=> $1::vector) AS cos_sim
               FROM chunks WHERE pr_id = $2
               ORDER BY embedding <=> $1::vector""",
            to_literal(query_vec),
            pr_id,
        )

        print("  cosine similarity vs 'identical':")
        expected = {"identical": 1.0, "double_magnitude": 1.0, "orthogonal": 0.0, "opposite": -1.0}
        for r in rows:
            got, want = r["cos_sim"], expected[r["label"]]
            flag = "ok " if abs(got - want) < 1e-5 else "FAIL"
            print(f"    {flag} {r['label']:<18} {got:+.7f}  (expected {want:+.1f})")
            assert abs(got - want) < 1e-5, f"{r['label']}: {got} != {want}"

        # float4 storage: what does the round trip actually cost?
        raw = await conn.fetchval(
            "SELECT embedding::text FROM chunks WHERE pr_id=$1 AND hunk_index=0", pr_id
        )
        # was: back = np.fromstring(raw.strip("[]"), sep=",")
        back = np.array(raw.strip("[]").split(","), dtype=float)
        print(f"  max abs delta after round trip: {np.abs(back - query_vec).max():.3e}")
    finally:
        await tr.rollback()

    left = await conn.fetchval("SELECT count(*) FROM repos WHERE full_name='spike/day3'")
    print(f"  rows left behind: {left}")
    assert left == 0, "rollback did not clean up"


async def check_wrong_dimension(conn: asyncpg.Connection) -> None:
    short = "[" + ",".join(["0.1"] * (EMBEDDING_DIM - 1)) + "]"
    try:
        await conn.fetchval(f"SELECT $1::vector({EMBEDDING_DIM})", short)
        print("  ! wrong-dimension vector was ACCEPTED — column is not enforcing dims")
    except asyncpg.PostgresError as e:
        print(f"  wrong dimension rejected: {type(e).__name__}")


async def run_target(name: str, dsn: str, **kwargs) -> None:
    print(f"\n=== {name} ===")
    try:
        conn = await asyncpg.connect(dsn, **kwargs)
    except Exception as e:
        print(f"  CONNECT FAILED: {type(e).__name__}: {e}")
        return
    try:
        print(f"  server: {(await conn.fetchval('SELECT version()')).split(',')[0]}")
        await check_schema(conn)
        await round_trip(conn, build_vectors())
        await check_wrong_dimension(conn)
        print(f"  {name}: PASS")
    finally:
        await conn.close()


async def main() -> None:
    local = "postgresql://postgres:dev@localhost/prreview"
    direct = os.environ["DATABASE_URL_DIRECT"]
    pooled = os.environ["DATABASE_URL"]

    await run_target("local (docker pgvector)", local)
    await run_target("neon — direct", direct)
    # Phase 7 uses the pooled string. PgBouncer in transaction mode is the
    # known asyncpg failure mode; run it both ways to see which is true here.
    await run_target("neon — pooled, default cache", pooled)
    await run_target("neon — pooled, statement_cache_size=0", pooled, statement_cache_size=0)


if __name__ == "__main__":
    asyncio.run(main())
