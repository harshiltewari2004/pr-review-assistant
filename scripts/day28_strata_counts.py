"""Day 28: Area:* stratum sizes for query selection. 01 §8. Read-only."""

import asyncio

from ingest.db import connect

SQL = """
WITH p AS (
    SELECT pr.id, pr.created_at, pr.labels,
           cardinality(ARRAY(
               SELECT l FROM unnest(pr.labels) l WHERE l LIKE 'Area:%'
           )) AS n_area
    FROM pull_requests pr
    JOIN repos r ON r.id = pr.repo_id
    WHERE r.full_name = 'processing/p5.js' AND pr.in_corpus
)
SELECT l AS area,
       count(*)                            AS any_area,
       count(*) FILTER (WHERE n_area = 1)  AS single_area,
       min(created_at)::date               AS first,
       max(created_at)::date               AS last
FROM p, unnest(p.labels) l
WHERE l LIKE 'Area:%'
GROUP BY l
ORDER BY single_area DESC
"""

COVERAGE = """
SELECT count(*) FILTER (WHERE NOT labels && ARRAY(
           SELECT DISTINCT l FROM pull_requests, unnest(labels) l
           WHERE l LIKE 'Area:%'))          AS no_area,
       count(*)                              AS total
FROM pull_requests pr
JOIN repos r ON r.id = pr.repo_id
WHERE r.full_name = 'processing/p5.js' AND pr.in_corpus
"""


async def main() -> None:
    async with connect("local") as conn:
        for row in await conn.fetch(SQL):
            print(dict(row))
        print(dict(await conn.fetchrow(COVERAGE)))


asyncio.run(main())
