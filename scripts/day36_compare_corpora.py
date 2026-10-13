"""Day 36: id-independent corpus comparison, local vs Neon (D-P7-3).

The D-P5-9 fingerprint hashes row ids, and the two databases assigned
different ids (local repo_id 2, Neon 1). This hashes CONTENT keyed by PR
number and (number, file_path, hunk_index). If local and Neon match,
production serves the same corpus that was evaluated.

COLLATE "C" forces byte-order sorting: the two servers' default collations
may order punctuation or case differently, which would change the hash of
identical content.

Usage: python -m scripts.day36_compare_corpora
"""

from __future__ import annotations

import asyncio
import hashlib
import json

import numpy as np

from ingest.db import connect

REPO = "processing/p5.js"
PRS_SQL = """
SELECT number, in_corpus, created_at, title, body, files_changed
FROM pull_requests WHERE repo_id = $1 ORDER BY number
"""
CHUNKS_SQL = """
SELECT p.number, c.file_path, c.hunk_index, c.embedding
FROM chunks c JOIN pull_requests p ON p.id = c.pr_id
WHERE c.repo_id = $1
ORDER BY p.number, c.file_path COLLATE "C", c.hunk_index
"""


async def content_fingerprint(target: str) -> tuple[int, int, str]:
    async with connect(target) as conn:
        rid = await conn.fetchval("SELECT id FROM repos WHERE full_name = $1", REPO)
        prs = await conn.fetch(PRS_SQL, rid)
        chunks = await conn.fetch(CHUNKS_SQL, rid)
    h = hashlib.sha256()
    for r in prs:
        record = [
            r["number"],
            r["in_corpus"],
            r["created_at"].isoformat(),
            r["title"],
            r["body"],
            list(r["files_changed"]),
        ]
        h.update(json.dumps(record).encode())
    for r in chunks:
        h.update(f"{r['number']}:{r['file_path']}:{r['hunk_index']}:".encode())
        h.update(r["embedding"].to_numpy().astype(np.float32).tobytes())
    return len(prs), len(chunks), h.hexdigest()


async def main() -> None:
    for target in ("local", "neon"):
        n_prs, n_chunks, fp = await content_fingerprint(target)
        print(f"{target:<6} prs={n_prs} chunks={n_chunks} content={fp[:16]}")


if __name__ == "__main__":
    asyncio.run(main())
