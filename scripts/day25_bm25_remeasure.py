"""Day 25 — re-measure BM25 corpus statistics after D-P4-5.

Baseline (Day 23, before the fix):
  avgdl 146.2 | median 102 | p90 303 | max 3,428 | min 4 | zero 0
  vocab 19,442 | average_idf 7.0609 | floor 1.765
  13 floored: the to of and in is for a this js p5 p 5
"""

import asyncio
import os
import statistics

import asyncpg

from app.retrieval.signals import build_bm25_index

REPO_ID = 2


async def main() -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL_LOCAL"])
    try:
        index = await build_bm25_index(conn, REPO_ID)
    finally:
        await conn.close()

    bm = index.bm25
    lens = sorted(bm.doc_len)
    n = len(lens)

    print(f"documents        {n}")
    print(f"avgdl            {bm.avgdl:.2f}")
    print(f"median           {statistics.median(lens):.0f}")
    print(f"p90              {lens[int(0.9 * n)]}")
    print(f"max              {max(lens)}")
    print(f"min              {min(lens)}")
    print(f"zero-token docs  {sum(1 for x in lens if x == 0)}")
    print()

    floor = bm.epsilon * bm.average_idf
    floored = sorted(t for t, v in bm.idf.items() if abs(v - floor) < 1e-12)

    print(f"vocabulary       {len(bm.idf)}")
    print(f"average_idf      {bm.average_idf:.4f}")
    print(f"epsilon          {bm.epsilon}")
    print(f"floor            {floor:.3f}")
    print(f"floored terms    {len(floored)}: {' '.join(floored)}")
    print(f"max idf          {max(bm.idf.values()):.2f}")


if __name__ == "__main__":
    asyncio.run(main())