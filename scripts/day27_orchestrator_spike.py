"""Day 27 spike: first end-to-end run of find_similar_prs() on #8994.

Explains |C| via per-signal nomination overlap, measures backfill latency
(D-P4-10), and runs golden assertions. Print and read: no error != correct.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

import numpy as np

from app.retrieval.constants import BM25_TOP_K, FILE_OVERLAP_TOP_K, VECTOR_TOP_K
from app.retrieval.scoring import _nominate, find_similar_prs
from app.retrieval.signals import (
    bm25_scores,
    build_bm25_index,
    build_document,
    file_overlap_signal,
    vector_signal_for_pr,
)
from ingest.db import connect

REPO_ID = 2
QUERY_NUMBER = 8994

_STD_FIELDS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class ExtraFormatter(logging.Formatter):
    """basicConfig drops `extra`; this prints it. Spike-only, not 04 §10's."""

    def format(self, record: logging.LogRecord) -> str:
        extras = {k: v for k, v in record.__dict__.items() if k not in _STD_FIELDS}
        return f"{record.getMessage()} {json.dumps(extras, default=str)}"


async def main() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(ExtraFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])

    async with connect("local") as conn:
        q = await conn.fetchrow(
            "SELECT id, created_at, title, body, files_changed FROM pull_requests "
            "WHERE repo_id = $1 AND number = $2",
            REPO_ID,
            QUERY_NUMBER,
        )
        rows = await conn.fetch(
            "SELECT embedding FROM chunks WHERE pr_id = $1 ORDER BY file_path, hunk_index",
            q["id"],
        )
        embeddings = [r["embedding"].to_numpy().astype(np.float32) for r in rows]
        tokens = build_document(q["title"], q["body"], q["files_changed"])
        index = await build_bm25_index(conn, REPO_ID)
        print(
            f"query #{QUERY_NUMBER}: id={q['id']} chunks={len(embeddings)} "
            f"files={len(q['files_changed'])} tokens={len(tokens)}"
        )

        # Nominations recomputed here ONLY to explain |C|; the orchestrator
        # does its own. Costs one extra round of signal queries.
        vec = await vector_signal_for_pr(conn, embeddings, REPO_ID, q["created_at"], q["id"])
        fil = await file_overlap_signal(conn, q["files_changed"], REPO_ID, q["created_at"], q["id"])
        bm = bm25_scores(index, tokens, q["created_at"], q["id"])
        v = set(_nominate({k: a.score_raw for k, a in vec.items()}, VECTOR_TOP_K))
        f = set(_nominate(fil, FILE_OVERLAP_TOP_K))
        b = set(_nominate(bm, BM25_TOP_K))
        print(
            f"|V|={len(v)} |F|={len(f)} |B|={len(b)}  "
            f"V∩F={len(v & f)} V∩B={len(v & b)} F∩B={len(f & b)} "
            f"V∩F∩B={len(v & f & b)}  |C|={len(v | f | b)}"
        )

        started = time.perf_counter()
        results = await find_similar_prs(
            conn,
            index,
            repo_id=REPO_ID,
            query_pr_id=q["id"],
            query_created_at=q["created_at"],
            query_embeddings=embeddings,
            query_files=q["files_changed"],
            query_tokens=tokens,
        )
        print(f"find_similar_prs total: {(time.perf_counter() - started) * 1000:.1f} ms")

        ids = [r.pr_id for r in results]
        meta = {
            r["id"]: r
            for r in await conn.fetch(
                "SELECT id, number, title, created_at FROM pull_requests "
                "WHERE id = ANY($1::bigint[])",
                ids,
            )
        }
        for rank, r in enumerate(results, 1):
            pr_id, score = r.pr_id, r.final_score
            m = meta[pr_id]
            print(f"  {rank}. #{m['number']}  {score:.4f}  {m['title']}")

        # Golden assertions (rule 20).
        assert len(results) == 3, f"expected 3 results, got {len(results)}"
        assert all(0.0 <= r.final_score <= 1.0 for r in results), "invariant 5: score outside [0,1]"
        assert all(
            0.0 <= v <= 1.0
            for r in results
            for v in (r.vector_score_norm, r.file_overlap_score_norm, r.bm25_score_norm)
        ), "norm outside [0,1]"
        scores = [r.final_score for r in results]
        assert scores == sorted(scores, reverse=True), "results not best-first"
        assert q["id"] not in ids, "query PR retrieved itself"
        assert all(meta[i]["created_at"] < q["created_at"] for i in ids), "invariant 1 LEAK"
        print("golden assertions: PASS")


if __name__ == "__main__":
    asyncio.run(main())
