"""Retrieval signals. 03 §5-§7.
Computes raw signal values only. Normalization is normalize.py (03 §8),
ranking is scoring.py 06 §10, one concept per module.

Takes an open asyncpg connection rather than acquiring one, so scripts/,
app/,and eval/ can reach supply their own without app/ importing ingest/
(06 §10) or eval/ (invariant 12).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import asyncpg
import numpy as np

from app.retrieval.constants import EMBEDDING_DIM, MEAN_TOP_K, VECTOR_AGGREGATION, VECTOR_TOP_K

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


@dataclass(frozen=True, slots=True)
class VectorAggregate:
    """One candidate PR's vector signal, collapsed across the query PR's chunks.

    chunk_hints is not decoration. Each per-chunk query is capped at
    VECTOR_TOP_K, so a candidate absent from a chunk's result list did NOT
    score zero - it scored below that list's cutoff. Aggregating over
    observed values only is therefore biased, and chunk_hits is the evidence
    count that makes the bias measurable at Day 34 instead of silent.
    """

    score_raw: float
    chunk_hits: int


def aggregate_chunk_scores(
    per_candidate: dict[int, list[float]],
    strategy: str = VECTOR_AGGREGATION,
) -> dict[int, VectorAggregate]:
    """Collapses per-query-chunk scores into one score per candidate PR.

    Pure:no I/O, no async. The DB loops lives in the caller so this stays
    unit-testable without a database.

    MAX is order-independent and associative, so composing it with the SQL's
    candidates chunks is exactly MAX over all(query chunk,candidate chunk) pairs -— 03 §5.
    mean_to_k is not associative, so it averages the top MEAN_TOP_K *query-chunk* values, not pair
    values; the pair-level version would need a second query without GROUP BY.
    Deviation recorded as D-P3-3.
    """

    if strategy not in ("max", "mean_top_k"):
        raise ValueError(f"unknown aggregation strategy:{strategy!r}")

    out: dict[int, VectorAggregate] = {}
    for pr_id, scores in per_candidate.items():
        if not scores:
            raise ValueError(f"candidate {pr_id} collected with no scores")
        if strategy == "max":
            value = max(scores)
        else:
            top = sorted(scores, reverse=True)[:MEAN_TOP_K]
            value = sum(top) / len(top)
        out[pr_id] = VectorAggregate(score_raw=value, chunk_hits=len(scores))

    return out


async def vector_signal_for_pr(
    conn: asyncpg.Connection,
    query_embeddings: list[np.ndarray],
    repo_id: int,
    query_created_at: datetime,
    query_pr_id: int,
    strategy: str = VECTOR_AGGREGATION,
) -> dict[int, VectorAggregate]:
    """The vector signal for one query PR, across all of its chunks.

    Returns every candidates the per-chunk queries surfaced, uncut and
    unranked. CANDIDATE_TOP_N and the union with the other two signals are
    scoring.py's job (03 §4)-06 §10 keeps ranking out of this module.

    Queries run sequentially: an asyncpg Connection cannot carry concurrent
    operations, so overlapping them needs a pool, not a loop change. At ~13
    chunks x ~27 ms median this is ~350 ms server-side(Day 17 measurement).
    """

    if not query_embeddings:
        raise ValueError(f"query PR{query_pr_id} has no chunk embeddings")

    per_candidate: dict[int, list[float]] = defaultdict(list)
    for embedding in query_embeddings:
        rows = await vector_signal(conn, embedding, repo_id, query_created_at, query_pr_id)

        for pr_id, score_raw in rows:
            per_candidate[pr_id].append(score_raw)

    return aggregate_chunk_scores(dict(per_candidate), strategy)


def jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    """Jaccard similarity between two file-path sets.

    Exact path matching (03 §6) - no directory-prefix credit.

    Either side empty returns 0.0 rather than raising:an in-corpus PR
    always has source files, so an empty side means bad input, and a
    silent 0.0 is the right answer for a signal that carries no
    information  about that pair.
    """
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


# 03 §4 step 4. `&&` is array-overlap: true iff the intersection is
# non-empty. Uses idx_pr_files (GIN, 02 §4). The prefilter is lossless —
# a PR it drops has an empty intersection, so J = 0.0 by definition.
# Contrast VECTOR_TOP_K, where exclusion means "below the cutoff",
# an unknown value. Jaccard itself is computed in Python (03 §6).
FILE_CANDIDATES_SQL = """
    SELECT p.id,p.files_changed
    FROM pull_requests p
    WHERE p.repo_id=$2
        AND p.in_corpus
        AND p.created_at <$3
        AND p.id<>$4
        AND p.files_changed && $1::text[]
"""

# 03 §7 tokenization. The spec's numbered list describes the OUTPUT, not
# an execution order: lowercasing first would destroy the camelCase
# boundaries step 3 needs, and treating `_` as non-alphanumeric would
# destroy the whole identifier step 4 requires.
#
# _IDENTIFIER keeps `_` and case so both survive to the split.
# _SUBTOKEN alternatives, in order:
#   [A-Z]+(?=[A-Z][a-z])  acronym run before a capitalized word:
#                         parseHTTPResponse -> HTTP, not HTTPR
#   [A-Z]?[a-z]+          optional capital + lowercase run: Sse, format
#   [A-Z]+                trailing all-caps run: parseURL -> URL
#   \d+                   digit runs split off: p5Vector -> p5 ... see below

_IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")
_SUBTOKEN = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def tokenize(text: str) -> list[str]:
    """Text ->BM25 terms. 03 §7.

    Emits the whole identifier AND its sub-tokens:`jsonable_encoder`
    yields all three of jsonable_encoder,jsonable,encoder. A PR whose
    title says "encoder" then partially matches one that says
    `jsonable_encoder`,while an exact reference to the full identifier
    still scores highest.Losing either behavior loses real matches.

    Returns a list, not a set:BM25 weighs by term frequency,so
    repeated terms must stay repeated.
    """
    tokens: list[str] = []
    for identifier in _IDENTIFIER.findall(text):
        whole = identifier.lower()
        tokens.append(whole)
        parts = [p.lower() for p in _SUBTOKEN.findall(identifier)]
        if len(parts) > 1:
            tokens.extend(parts)

    return tokens


def build_document(
    title: str,
    body: str | None,
    files_changed: Sequence[str],
) -> list[str]:
    """One PR -> its BM25 term list.03 §7.

    title+body+basenames of files_changed. Basenames, not full paths:
    full paths would put src/core/webgl in nearly every document, which is
    directory structure rather than content - and path-level similarity is
    already the file-overlap signal's job (03 §6).

    body is optional because Github permits an empty PR description;a
    None here is ordinary,not an error.
    """
    parts = [title, body or ""]
    parts.extend(path.rsplit("/", 1)[-1] for path in files_changed)
    return tokenize("\n".join(parts))
