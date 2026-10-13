"""The analyze pipeline, shared by POST /analyze and the GitHub Action.

One function, so the API and the Action can never drift: diff -> chunks ->
embeddings -> retrieval -> reasons -> results. Chunks and files come from the
same parse_hunks / files_changed / h.content path as indexing. D-P7-1, D-P7-3.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import numpy as np

from app.retrieval.chunking import files_changed, parse_hunks
from app.retrieval.embedding import embed
from app.retrieval.reasons import explain
from app.retrieval.scoring import find_similar_prs
from app.retrieval.signals import build_document
from app.schemas import AnalyzeResult

# A PR not in the corpus has no row: nothing to exclude, and "the past" is
# everything created before now. Ids are BIGSERIAL, so -1 matches nothing.
NEW_PR_ID = -1
SCORE_DECIMALS = 4

REPO_SQL = "SELECT id FROM repos WHERE full_name = $1"
CORPUS_COUNT_SQL = "SELECT count(*) FROM pull_requests WHERE repo_id = $1 AND in_corpus"
KNOWN_PR_SQL = "SELECT id, created_at FROM pull_requests WHERE repo_id = $1 AND number = $2"
RESULT_META_SQL = (
    "SELECT id, number, title, outcome FROM pull_requests WHERE id = ANY($1::bigint[])"
)


async def analyze_diff(
    conn,
    index,
    *,
    repo: str,
    repo_id: int,
    title: str,
    body: str | None,
    diff: str,
    known_pr_number: int | None,
) -> list[AnalyzeResult]:
    """Top results for one diff. known_pr_number: look the PR up in the corpus
    (its own created_at, never itself). None: treat it as brand new (D-P7-3)."""
    hunks = parse_hunks(diff)
    if not hunks:  # docs-only or excluded-only diff: nothing to compare
        return []

    vectors = await asyncio.to_thread(embed, [h.content for h in hunks])
    embeddings = [v.astype(np.float32) for v in vectors]
    files = files_changed(hunks)
    tokens = build_document(title, body, files)

    known = None
    if known_pr_number is not None:
        known = await conn.fetchrow(KNOWN_PR_SQL, repo_id, known_pr_number)

    results = await find_similar_prs(
        conn,
        index,
        repo_id=repo_id,
        query_pr_id=known["id"] if known else NEW_PR_ID,
        query_created_at=known["created_at"] if known else datetime.now(UTC),
        query_embeddings=embeddings,
        query_files=files,
        query_tokens=tokens,
    )
    reasons = await explain(conn, index, query_files=files, query_tokens=tokens, results=results)
    meta = {m["id"]: m for m in await conn.fetch(RESULT_META_SQL, [r.pr_id for r in results])}

    return [
        AnalyzeResult(
            pr_number=meta[r.pr_id]["number"],
            title=meta[r.pr_id]["title"],
            url=f"https://github.com/{repo}/pull/{meta[r.pr_id]['number']}",
            outcome=meta[r.pr_id]["outcome"],
            final_score=round(r.final_score, SCORE_DECIMALS),
            vector_score_norm=round(r.vector_score_norm, SCORE_DECIMALS),
            file_overlap_score_norm=round(r.file_overlap_score_norm, SCORE_DECIMALS),
            bm25_score_norm=round(r.bm25_score_norm, SCORE_DECIMALS),
            reason=reason,
        )
        for r, reason in zip(results, reasons, strict=True)
    ]
