"""End-to-end retrieval against a fixture corpus. 07 §6, 07 §4.

Invariant 1 is enforced in SQL — VECTOR_SIGNAL_SQL and FILE_CANDIDATES_SQL
both carry `p.created_at < $3`. A pure-function test downstream of those
queries cannot see the clause it claims to guard, which is why this file
exists and why test_scoring.py's version of this assertion was deleted.

The fixture corpus is deliberately hostile where the real corpus is not.
Real timestamps are spread out, so `created_at == query.created_at` almost
never occurs — and that is the exact case a `<=` typo passes. Here it is
constructed on purpose.

Embeddings and file lists are IDENTICAL across all four fixture PRs, so
cosine is 1.0 and Jaccard is 1.0 for every candidate. Nothing but the
temporal clause can exclude anything. If the clause breaks, every
assertion below fails loudly instead of one edge case slipping through.

Synthetic vectors, not MiniLM output: the clause is `created_at < $3` and
does not read the vector. Loading the model would cost ~360 MB, several
seconds, and a model download that 07 §7 forbids — for no extra coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg
import numpy as np
import pytest
import pytest_asyncio

from app.retrieval.scoring import build_candidate_set
from app.retrieval.signals import file_overlap_signal, vector_signal_for_pr

QUERY_TIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
SHARED_FILES = ["src/core/main.js", "src/math/p5.Vector.js"]


@dataclass(frozen=True)
class FixtureCorpus:
    """pr_ids of the four fixture PRs, by their relation to QUERY_TIME."""

    repo_id: int
    query: int
    before: int
    equal: int
    after: int


async def _insert_pr(
    conn: asyncpg.Connection, repo_id: int, number: int, created_at: datetime
) -> int:
    """One in-corpus PR with SHARED_FILES and one chunk carrying a ones-vector."""
    pr_id: int = await conn.fetchval(
        """
        INSERT INTO pull_requests (
            repo_id, number, github_id, title, author, author_type,
            outcome, files_changed, created_at, in_corpus
        ) VALUES ($1, $2, $3, $4, 'fixture-author', 'User',
                  'merged', $5, $6, TRUE)
        RETURNING id
        """,
        repo_id,
        number,
        900_000 + number,
        f"fixture PR {number}",
        SHARED_FILES,
        created_at,
    )
    await conn.execute(
        """
        INSERT INTO chunks (
            pr_id, repo_id, file_path, hunk_index, content,
            token_count, was_truncated, embedding
        ) VALUES ($1, $2, $3, 0, $4, 12, FALSE, $5)
        """,
        pr_id,
        repo_id,
        SHARED_FILES[0],
        f"fixture hunk for PR {number}",
        np.ones(384, dtype=np.float32),
    )
    return pr_id


@pytest_asyncio.fixture
async def corpus(db: asyncpg.Connection) -> FixtureCorpus:
    """Four PRs straddling QUERY_TIME. Rolled back by the db fixture."""
    repo_id: int = await db.fetchval(
        """
        INSERT INTO repos (github_id, owner, name, full_name, status)
        VALUES (999999, 'fixture', 'corpus', 'fixture/corpus', 'ready')
        RETURNING id
        """
    )
    return FixtureCorpus(
        repo_id=repo_id,
        query=await _insert_pr(db, repo_id, 100, QUERY_TIME),
        before=await _insert_pr(db, repo_id, 101, QUERY_TIME - timedelta(days=1)),
        equal=await _insert_pr(db, repo_id, 102, QUERY_TIME),
        after=await _insert_pr(db, repo_id, 103, QUERY_TIME + timedelta(days=1)),
    )


@pytest.mark.asyncio
async def test_vector_signal_excludes_non_past_candidates(
    db: asyncpg.Connection, corpus: FixtureCorpus
) -> None:
    """Invariant 1 through VECTOR_SIGNAL_SQL. 07 §4, temporal filter.

    `equal` catches `<=`; `after` catches a missing clause; `query` catches
    a missing `p.id <> $4`. All four vectors are identical, so cosine cannot
    be what excludes them.
    """
    result = await vector_signal_for_pr(
        db,
        [np.ones(384, dtype=np.float32)],
        corpus.repo_id,
        QUERY_TIME,
        corpus.query,
    )

    assert set(result) == {corpus.before}


@pytest.mark.asyncio
async def test_file_overlap_signal_excludes_non_past_candidates(
    db: asyncpg.Connection, corpus: FixtureCorpus
) -> None:
    """Invariant 1 through FILE_CANDIDATES_SQL, the second SQL enforcement site.

    Every fixture PR has SHARED_FILES, so Jaccard is 1.0 for all of them and
    only the temporal clause can cut anything.
    """
    result = await file_overlap_signal(db, SHARED_FILES, corpus.repo_id, QUERY_TIME, corpus.query)

    assert set(result) == {corpus.before}


@pytest.mark.asyncio
async def test_candidate_set_inherits_the_temporal_filter(
    db: asyncpg.Connection, corpus: FixtureCorpus
) -> None:
    """The union of two real signal queries carries no leak forward.

    build_candidate_set() has no temporal logic of its own — it unions what
    the signals hand it (invariant 3). This asserts the composition, which
    is the only thing a set union can be held responsible for.
    """
    vector_raw = {
        pr_id: agg.score_raw
        for pr_id, agg in (
            await vector_signal_for_pr(
                db, [np.ones(384, dtype=np.float32)], corpus.repo_id, QUERY_TIME, corpus.query
            )
        ).items()
    }
    file_raw = await file_overlap_signal(db, SHARED_FILES, corpus.repo_id, QUERY_TIME, corpus.query)

    candidates = build_candidate_set(vector_raw, file_raw, {})

    assert candidates.ids == [corpus.before]
    assert corpus.query not in candidates.ids


@pytest.mark.skip(reason="needs rank_candidates() and reasons.py — 07 §6 structural half")
def test_results_carry_all_three_normalized_scores_and_a_reason() -> None:
    """07 §6's remaining three assertions: exactly 3 results, all three
    normalized signal scores present, non-empty reason string.

    Deliberately skipped, not omitted. These need the orchestrator (next item)
    and reasons.py (blocked on D-P4-11). 09 §5's hard deadline is the temporal
    filter, which the three tests above satisfy; the rest is output shape and
    cannot leak. Visible as skipped so it can't be quietly forgotten.
    """
