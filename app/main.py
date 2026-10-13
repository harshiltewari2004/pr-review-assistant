"""FastAPI service. 04 §4: GET /health and POST /analyze; GET /similar comes later.

The lifespan does the expensive work once: DB pool, repo lookup, BM25 index
(reads the whole corpus, 03 §7), embedding model (04 §7). A request then only
embeds its own diff and queries.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Request

from app.auth import require_api_key
from app.config import get_settings
from app.db import create_pool
from app.retrieval.chunking import files_changed, parse_hunks
from app.retrieval.embedding import embed, get_model
from app.retrieval.reasons import explain
from app.retrieval.scoring import find_similar_prs
from app.retrieval.signals import build_bm25_index, build_document
from app.schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeResult

log = logging.getLogger(__name__)

# A PR not yet in the corpus has no row: nothing to exclude, and "the past"
# is everything created before now. Ids are BIGSERIAL, so -1 matches nothing.
NEW_PR_ID = -1
SCORE_DECIMALS = 4

REPO_SQL = "SELECT id FROM repos WHERE full_name = $1"
CORPUS_COUNT_SQL = "SELECT count(*) FROM pull_requests WHERE repo_id = $1 AND in_corpus"
KNOWN_PR_SQL = "SELECT id, created_at FROM pull_requests WHERE repo_id = $1 AND number = $2"
RESULT_META_SQL = (
    "SELECT id, number, title, outcome FROM pull_requests WHERE id = ANY($1::bigint[])"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.model_loaded = False
    pool = await create_pool(settings.database_url)
    async with pool.acquire() as conn:
        repo_id = await conn.fetchval(REPO_SQL, settings.repo)
        if repo_id is None:
            raise RuntimeError(f"repo {settings.repo!r} is not indexed")
        app.state.index = await build_bm25_index(conn, repo_id)
        app.state.corpus_prs = await conn.fetchval(CORPUS_COUNT_SQL, repo_id)
    await asyncio.to_thread(get_model)  # 04 §7: load once, never per request
    app.state.pool = pool
    app.state.repo = settings.repo
    app.state.repo_id = repo_id
    app.state.model_loaded = True
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health(request: Request) -> dict:
    """Cheap readiness for the Action's warmup loop (04 §7). No DB on the hot path."""
    state = request.app.state
    return {
        "status": "ok",
        "model_loaded": getattr(state, "model_loaded", False),
        "corpus_prs": getattr(state, "corpus_prs", 0),
    }


@app.post("/analyze", response_model=AnalyzeResponse, dependencies=[Depends(require_api_key)])
async def analyze(req: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    state = request.app.state
    if req.repo != state.repo:
        raise HTTPException(status_code=404, detail=f"repo {req.repo!r} is not indexed")

    hunks = parse_hunks(req.diff)
    if not hunks:  # docs-only or excluded-only diff: nothing to compare
        return AnalyzeResponse(query_pr=req.pr_number, results=[])

    request_id = uuid.uuid4().hex[:12]
    try:
        vectors = await asyncio.to_thread(embed, [h.content for h in hunks])
        embeddings = [v.astype(np.float32) for v in vectors]
        files = files_changed(hunks)
        tokens = build_document(req.title, req.body, files)
        async with state.pool.acquire() as conn:
            known = await conn.fetchrow(KNOWN_PR_SQL, state.repo_id, req.pr_number)
            results = await find_similar_prs(
                conn,
                state.index,
                repo_id=state.repo_id,
                query_pr_id=known["id"] if known else NEW_PR_ID,
                query_created_at=known["created_at"] if known else datetime.now(UTC),
                query_embeddings=embeddings,
                query_files=files,
                query_tokens=tokens,
            )
            reasons = await explain(
                conn, state.index, query_files=files, query_tokens=tokens, results=results
            )
            meta_rows = await conn.fetch(RESULT_META_SQL, [r.pr_id for r in results])
    except Exception as exc:
        # 04 §10: retrieval failure is 503 (retryable), with a request id to grep.
        log.exception("analyze failed", extra={"request_id": request_id, "pr": req.pr_number})
        raise HTTPException(
            status_code=503, detail={"error": "retrieval failed", "request_id": request_id}
        ) from exc

    meta = {m["id"]: m for m in meta_rows}
    return AnalyzeResponse(
        query_pr=req.pr_number,
        results=[
            AnalyzeResult(
                pr_number=meta[r.pr_id]["number"],
                title=meta[r.pr_id]["title"],
                url=f"https://github.com/{state.repo}/pull/{meta[r.pr_id]['number']}",
                outcome=meta[r.pr_id]["outcome"],
                final_score=round(r.final_score, SCORE_DECIMALS),
                vector_score_norm=round(r.vector_score_norm, SCORE_DECIMALS),
                file_overlap_score_norm=round(r.file_overlap_score_norm, SCORE_DECIMALS),
                bm25_score_norm=round(r.bm25_score_norm, SCORE_DECIMALS),
                reason=reason,
            )
            for r, reason in zip(results, reasons, strict=True)
        ],
    )
