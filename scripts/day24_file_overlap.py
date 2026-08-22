"""Day 24 — file_overlap_signal() first run. 03 §4 step 4, 03 §6.

Golden assertion: every returned value is > 0.0. `&&` is true only when the
intersection is non-empty, so J = |A n B| / |A u B| has a numerator of at
least 1 for every row. A 0.0 in this dict means the SQL and the scoring
loop disagree about what was fetched.
"""

import asyncio
import os
from collections import Counter

import asyncpg

from app.retrieval.signals import file_overlap_signal

REPO_ID = 2
QUERY_NUMBER = 8994


async def main() -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL_LOCAL"])
    try:
        q = await conn.fetchrow(
            """
            SELECT id, number, files_changed, created_at, title
            FROM pull_requests
            WHERE repo_id = $1 AND number = $2
            """,
            REPO_ID,
            QUERY_NUMBER,
        )
        if q is None:
            raise SystemExit(f"PR #{QUERY_NUMBER} not found in repo_id={REPO_ID}")

        print(f"query: #{q['number']}  {q['title']}")
        print(f"created_at: {q['created_at']}")
        print(f"files ({len(q['files_changed'])}):")
        for path in q["files_changed"]:
            print(f"  {path}")

        scores = await file_overlap_signal(
            conn,
            q["files_changed"],
            REPO_ID,
            q["created_at"],
            q["id"],
        )

        print(f"\nfan-out: {len(scores)}")
        print(f"distinct J values: {len(set(scores.values()))}")

        # Golden assertion.
        zeros = [pr_id for pr_id, j in scores.items() if j <= 0.0]
        assert not zeros, f"J <= 0.0 for {len(zeros)} candidates: {zeros[:5]}"
        print("golden: all J > 0.0  OK")

        print("\nvalue histogram (J -> count), most common first:")
        for value, count in Counter(scores.values()).most_common(15):
            print(f"  {value:.4f}  x{count}")

        print("\ntop 10 by (-J, pr_id):")
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        numbers = await conn.fetch(
            "SELECT id, number, cardinality(files_changed) AS n FROM pull_requests"
            " WHERE id = ANY($1::bigint[])",
            [pr_id for pr_id, _ in ranked],
        )
        meta = {r["id"]: (r["number"], r["n"]) for r in numbers}
        for pr_id, j in ranked:
            number, n_files = meta[pr_id]
            print(f"  #{number:<6} J={j:.4f}  files={n_files}")
    finally:
        await conn.close()


asyncio.run(main())
