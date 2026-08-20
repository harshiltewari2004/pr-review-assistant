"""Retrieval signals. 03 §5-§7.
Computes raw signal values only. Normalization is normalize.py (03 §8),
ranking is scoring.py 06 §10, one concept per module.

Takes an open asyncpg connection rather than acquiring one, so scripts/,
app/,and eval/ can reach supply their own without app/ importing ingest/
(06 §10) or eval/ (invariant 12).
"""

from __future__ import annotations

from datetime import datetime

import asyncpg
import numpy as np

from app.retrieval.constants import EMBEDDING_DIM, VECTOR_TOP_K

# 03 §5. Invariant 1 lives in the WHERE clause below.
#
#   p.created_at < $3   TEMPORAL FILTER — mandatory, strict <.
#                       A candidate created after the query PR is
#                       information the system could not have had. A leak
#                       here invalidates every published number, not one run.
#   p.id <> $4          Belt-and-braces: strict < already excludes the query
#                       PR against itself. Kept for the replay case where
#                       two PRs share a created_at.
#   c.repo_id = $2      Denormalized (02 §5) — filters chunks before the
#                       join, not after.
#   $1                  No ::vector cast. register_vector (D-P3-1) types the
#                       parameter; Postgres infers vector from the <=>
#                       operator. The spec's cast predates that decision.
#
# Alias is vector_score_raw, not vector_score — invariant 6.

VECTOR_SIGNAL_SQL = """
SELECT c.pr_id,
    MAX(1-(c.embedding<=>$1))AS vector_score_raw
FROM chunks c
JOIN pull_requests p ON p.id = c.pr_id
WHERE c.repo_id = $2
    AND p.in_corpus
    AND p.created_at < $3
    AND p.id<>$4
GROUP BY c.pr_id
ORDER BY vector_score_raw DESC
LIMIT $5
"""


async def vector_signal(
    conn: asyncpg.Connection,
    query_embedding: np.ndarray,
    repo_id: int,
    query_created_at: datetime,
    query_pr_id: int,
    top_k: int = VECTOR_TOP_K,
) -> list[tuple[int, float]]:
    """One query chunk ->(pr_id,vector_score_raw),best first. 03 §5.

    Aggregates across CANDIDATE chunks only (SQL MAX). Aggregation across
    QUERY chunks is the caller's job -03  §5, Day 18.

    Raw score is in [-1,1], not [0,1].Do not clamp: normalize.py's
    per-query min-max needs the ordering intact (03 §8).
    """

    if query_embedding.shape != (EMBEDDING_DIM,):
        raise ValueError(
            f"expected one {EMBEDDING_DIM}-dim vector,got shape {query_embedding.shape}"
        )

    # A naive datetime against TIMESTAMPTZ is interpreted in the session's
    # timezone, not UTC. That shifts the temporal boundary by hours with no
    # error raised — invariant 1 failing silently. 02 §2 stores UTC.
    if query_created_at.tzinfo is None:
        raise ValueError("query_created at must be timezone-aware (02 §2)")

    rows = await conn.fetch(
        VECTOR_SIGNAL_SQL,
        query_embedding,
        repo_id,
        query_created_at,
        query_pr_id,
        top_k,
    )

    return [(r["pr_id"], r["vector_score_raw"]) for r in rows]
