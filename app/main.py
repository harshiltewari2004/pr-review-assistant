"""FastAPI service. 04 §4: GET /health and POST /analyze; GET /similar comes later.

The lifespan does the expensive work once: DB pool, repo lookup, BM25 index
(reads the whole corpus, 03 §7), embedding model (04 §7). The pipeline itself
lives in app.service, shared with the GitHub Action (D-P7-3).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request

from app.auth import require_api_key
from app.config import get_settings
from app.db import create_pool
from app.retrieval.embedding import get_model
from app.retrieval.signals import build_bm25_index
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.service import CORPUS_COUNT_SQL, REPO_SQL, analyze_diff

log = logging.getLogger(__name__)


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
    """Cheap readiness for a warmup loop (04 §7). No DB on the hot path."""
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

    request_id = uuid.uuid4().hex[:12]
    try:
        async with state.pool.acquire() as conn:
            results = await analyze_diff(
                conn,
                state.index,
                repo=state.repo,
                repo_id=state.repo_id,
                title=req.title,
                body=req.body,
                diff=req.diff,
                known_pr_number=req.pr_number,  # API callers name corpus PRs directly
            )
    except Exception as exc:
        # 04 §10: retrieval failure is 503 (retryable), with a request id to grep.
        log.exception("analyze failed", extra={"request_id": request_id, "pr": req.pr_number})
        raise HTTPException(
            status_code=503, detail={"error": "retrieval failed", "request_id": request_id}
        ) from exc

    return AnalyzeResponse(query_pr=req.pr_number, results=results)
