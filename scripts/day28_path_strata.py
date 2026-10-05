"""Day 28: src/<dir> stratum sizes by era, for D-P5-2 reopen. Read-only."""

import asyncio

from ingest.db import connect

BASE = """
FROM pull_requests pr
JOIN repos r ON r.id = pr.repo_id
WHERE r.full_name = 'processing/p5.js' AND pr.in_corpus
"""

BASE_FILES = BASE.replace("WHERE", ", unnest(pr.files_changed) fp WHERE")

BY_DIR = f"""
WITH f AS (
    SELECT pr.id, pr.created_at, split_part(fp, '/', 2) AS dir
    {BASE_FILES}
      AND fp LIKE 'src/%/%'
)
SELECT dir,
       count(DISTINCT id)                                                AS prs,
       count(DISTINCT id) FILTER (WHERE created_at <  '2024-01-01')      AS pre_2024,
       count(DISTINCT id) FILTER (WHERE created_at >= '2024-01-01')      AS from_2024
FROM f
GROUP BY dir
ORDER BY prs DESC
"""

SPREAD = f"""
WITH d AS (
    SELECT pr.id,
           (SELECT count(DISTINCT split_part(fp, '/', 2))
              FROM unnest(pr.files_changed) fp
             WHERE fp LIKE 'src/%/%') AS n_dirs
    {BASE}
)
SELECT count(*) FILTER (WHERE n_dirs = 0) AS no_src_dir,
       count(*) FILTER (WHERE n_dirs = 1) AS one_dir,
       count(*) FILTER (WHERE n_dirs > 1) AS multi_dir
FROM d
"""

# Subdirectories inside src/core/ — FES lived at src/core/friendly_errors/ in 1.x.
CORE_SUB = f"""
SELECT split_part(fp, '/', 3) AS sub, count(DISTINCT pr.id) AS prs
{BASE_FILES}
  AND fp LIKE 'src/core/%/%'
GROUP BY sub
ORDER BY prs DESC
"""

# FES across both layouts: 1.x src/core/friendly_errors/, 2.x src/friendly_errors/.
FES_TOTAL = f"""
SELECT count(DISTINCT pr.id)                                              AS fes_prs,
       count(DISTINCT pr.id) FILTER (WHERE pr.created_at <  '2024-01-01') AS pre_2024,
       count(DISTINCT pr.id) FILTER (WHERE pr.created_at >= '2024-01-01') AS from_2024
{BASE_FILES}
  AND (fp LIKE 'src/core/friendly_errors/%' OR fp LIKE 'src/friendly_errors/%')
"""


async def main() -> None:
    async with connect("local") as conn:
        print("--- by top-level dir")
        for row in await conn.fetch(BY_DIR):
            print(dict(row))
        print("--- spread")
        print(dict(await conn.fetchrow(SPREAD)))
        print("--- inside src/core/")
        for row in await conn.fetch(CORE_SUB):
            print(dict(row))
        print("--- FES, both layouts")
        print(dict(await conn.fetchrow(FES_TOTAL)))


asyncio.run(main())
