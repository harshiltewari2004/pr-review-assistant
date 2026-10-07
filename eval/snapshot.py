"""Corpus snapshot + fingerprint. 01 §15, invariant 13. D-P5-9 W2.

01 §15 requires a committed corpus_snapshot.json: the filtered PR set and its
ingest timestamp. The fingerprint is a SHA-256 over everything retrieval
reads: PR metadata (corpus filter, temporal filter, BM25 inputs) and chunk
embeddings. A re-ingest, a flipped in_corpus flag, or a re-embed (e.g. an
unpinned sentence-transformers) changes it. pool.json carries the same
fingerprint; score.py must refuse to run when the live corpus no longer matches.

No wall-clock field: the same corpus gives a byte-identical file.

Usage: python -m eval.snapshot
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import numpy as np

from ingest.db import connect

REPO_ID = 2
SNAPSHOT_PATH = Path(__file__).parent / "artifacts" / "corpus_snapshot.json"

PRS_SQL = """
SELECT id, number, in_corpus, created_at, title, body, files_changed
FROM pull_requests WHERE repo_id = $1 ORDER BY id
"""
CHUNKS_SQL = "SELECT id, pr_id, embedding FROM chunks WHERE repo_id = $1 ORDER BY id"
REPO_SQL = "SELECT full_name, indexed_at FROM repos WHERE id = $1"


def fingerprint_rows(prs, chunks) -> str:
    """SHA-256 over PR rows, then chunk rows, each in id order. Pure.

    Each PR record is a JSON array (self-delimiting); each chunk is
    "id:pr_id:" plus a fixed-length float32 vector. No two different
    inputs can concatenate to the same byte stream.
    """
    h = hashlib.sha256()
    for r in prs:
        record = [
            r["id"],
            r["in_corpus"],
            r["created_at"].isoformat(),
            r["title"],
            r["body"],
            list(r["files_changed"]),
        ]
        h.update(json.dumps(record).encode())
    for r in chunks:
        h.update(f"{r['id']}:{r['pr_id']}:".encode())
        h.update(r["embedding"].to_numpy().astype(np.float32).tobytes())
    return h.hexdigest()


async def corpus_fingerprint(conn, repo_id: int) -> str:
    """Fingerprint of the live corpus. Used by pool.py now, score.py later."""
    prs = await conn.fetch(PRS_SQL, repo_id)
    chunks = await conn.fetch(CHUNKS_SQL, repo_id)
    return fingerprint_rows(prs, chunks)


async def main() -> None:
    async with connect("local") as conn:
        repo = await conn.fetchrow(REPO_SQL, REPO_ID)
        prs = await conn.fetch(PRS_SQL, REPO_ID)
        chunks = await conn.fetch(CHUNKS_SQL, REPO_ID)

    assert repo["indexed_at"] is not None, "repos.indexed_at is NULL: no ingest timestamp"
    payload = {
        "repo": repo["full_name"],
        "indexed_at": repo["indexed_at"].isoformat(),
        "corpus_fingerprint": fingerprint_rows(prs, chunks),
        "pr_count": len(prs),
        "in_corpus_count": sum(1 for r in prs if r["in_corpus"]),
        "chunk_count": len(chunks),
        "in_corpus_pr_numbers": sorted(r["number"] for r in prs if r["in_corpus"]),
    }
    SNAPSHOT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        f"{payload['repo']}  indexed_at={payload['indexed_at']}\n"
        f"prs={payload['pr_count']}  in_corpus={payload['in_corpus_count']}  "
        f"chunks={payload['chunk_count']}\n"
        f"fingerprint={payload['corpus_fingerprint']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
