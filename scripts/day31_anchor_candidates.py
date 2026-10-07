"""Day 31: dump anchor candidate pairs for the 01 §7 rewrite (D-P5-12).

Queries are NOT eval queries, so no pair here is in eval/artifacts/pool.json:
anchors are open rubric examples (D-P5-1) and must not pre-judge a blind label.
Per query: top 3 by the default hybrid + the bottom of C (a likely grade 0).
Query is always the LATER PR (temporal rule, 01 §5).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import numpy as np

from app.retrieval.scoring import build_backfilled_candidates, rank_candidates
from app.retrieval.signals import build_bm25_index, build_document
from eval.label import PR_SQL, render
from ingest.db import connect

REPO_ID = 2
ANCHOR_QUERIES = [8933, 8994]
EXTRA_PAIRS = [(8933, 8829)]  # verified grade-2 anchor (01 §7), query = later PR

Q_SQL = """
SELECT id, created_at, title, body, files_changed
FROM pull_requests WHERE repo_id = $1 AND number = $2
"""


async def main() -> None:
    pool = json.loads(Path("eval/artifacts/pool.json").read_text())
    eval_ids = {e["query_pr_id"] for e in pool["queries"]}

    async with connect("local") as conn:
        index = await build_bm25_index(conn, REPO_ID)
        pairs: list[tuple[int, int]] = []

        for number in ANCHOR_QUERIES:
            q = await conn.fetchrow(Q_SQL, REPO_ID, number)
            assert q["id"] not in eval_ids, f"#{number} is an eval query"
            rows = await conn.fetch(
                "SELECT embedding FROM chunks WHERE pr_id = $1 ORDER BY file_path, hunk_index",
                q["id"],
            )
            c = await build_backfilled_candidates(
                conn,
                index,
                repo_id=REPO_ID,
                query_pr_id=q["id"],
                query_created_at=q["created_at"],
                query_embeddings=[r["embedding"].to_numpy().astype(np.float32) for r in rows],
                query_files=q["files_changed"],
                query_tokens=build_document(q["title"], q["body"], q["files_changed"]),
            )
            ranked = rank_candidates(c, top_n=len(c.ids))
            pairs += [(q["id"], r.pr_id) for r in ranked[:3] + ranked[-1:]]

        for q_num, c_num in EXTRA_PAIRS:
            q = await conn.fetchrow(Q_SQL, REPO_ID, q_num)
            cand = await conn.fetchrow(Q_SQL, REPO_ID, c_num)
            assert cand["created_at"] < q["created_at"], "temporal rule"
            if (q["id"], cand["id"]) not in pairs:
                pairs.append((q["id"], cand["id"]))

        ids = {i for p in pairs for i in p}
        prs = {r["id"]: r for r in await conn.fetch(PR_SQL, list(ids))}
        for n, (q, c) in enumerate(pairs, 1):
            print("=" * 78)
            print(f"ANCHOR PAIR {n}")
            print(render(prs[q], "QUERY", show_outcome=False))
            print()
            print(render(prs[c], "CANDIDATE", show_outcome=True))


if __name__ == "__main__":
    asyncio.run(main())
