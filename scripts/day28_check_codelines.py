"""Day 28: golden check for changes_code() on three doc-titled draws."""

import asyncio

from eval.select_queries import REPO, changes_code
from ingest.db import connect

# Predicted before running: 6980 True, 7637 True, 8459 False.
NUMBERS = [8459, 7637, 6980]

SQL = """
SELECT pr.number, c.file_path, c.content
FROM chunks c
JOIN pull_requests pr ON pr.id = c.pr_id
JOIN repos r ON r.id = pr.repo_id
WHERE r.full_name = $1 AND pr.number = ANY($2::int[])
ORDER BY pr.number, c.file_path, c.hunk_index
"""


async def main() -> None:
    async with connect("local") as conn:
        rows = await conn.fetch(SQL, REPO, NUMBERS)
    by_pr: dict[int, list[bool]] = {}
    for row in rows:
        by_pr.setdefault(row["number"], []).append(changes_code(row["content"]))
    for number, flags in sorted(by_pr.items()):
        is_code = any(flags)
        print(f"#{number}: code chunks {sum(flags)}/{len(flags)} -> counts as code: {is_code}")


asyncio.run(main())
