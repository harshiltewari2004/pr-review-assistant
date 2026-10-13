"""GitHub Action entry point (D-P7-3): the runner is the compute.

Reads the corpus from Neon through a READ-ONLY role, runs
app.service.analyze_diff (the same function POST /analyze uses), and writes a
Markdown comment to $COMMENT_PATH. If there is nothing to compare, it writes
nothing, and the workflow posts nothing. The workflow marks this step
continue-on-error: this tool must never fail someone's PR (invariant 26).

Env:
  DATABASE_URL        read-only Neon URL (Actions secret)
  CORPUS_REPO         the indexed repo, e.g. processing/p5.js
  GITHUB_REPOSITORY   set by Actions: the repo the PR was opened in
  PR_NUMBER, PR_TITLE, PR_BODY, DIFF_PATH, COMMENT_PATH
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.db import create_pool
from app.retrieval.embedding import get_model
from app.retrieval.signals import build_bm25_index
from app.schemas import AnalyzeResult
from app.service import CORPUS_COUNT_SQL, REPO_SQL, analyze_diff

TOOL_URL = "https://github.com/harshiltewari2004/pr-review-assistant"


def render_comment(results: list[AnalyzeResult], corpus_repo: str, corpus_prs: int) -> str:
    """Markdown table: title + link next to each reason (D-P4-15: reasons
    alone can read identically in a tight cluster; titles tell them apart)."""
    lines = [
        "### Similar past pull requests",
        "",
        "| | Past PR | Why it may matter |",
        "|---|---|---|",
    ]
    for i, r in enumerate(results, start=1):
        title = r.title.replace("|", "\\|")
        reason = r.reason.replace("|", "\\|")
        lines.append(f"| {i} | [#{r.pr_number} {title}]({r.url}) | {reason} |")
    lines += [
        "",
        f"<sub>Hybrid retrieval (code embeddings + file overlap + BM25) over "
        f"{corpus_prs:,} past {corpus_repo} PRs. Scores are relative within this PR. "
        f"[How it works]({TOOL_URL})</sub>",
    ]
    return "\n".join(lines) + "\n"


async def run() -> None:
    env = os.environ
    corpus_repo = env["CORPUS_REPO"]
    diff = Path(env["DIFF_PATH"]).read_text()
    # D-P7-3: only a PR opened IN the corpus repo can be looked up by number.
    # A fork's PR #1 is not the corpus's PR #1.
    in_corpus_repo = env.get("GITHUB_REPOSITORY") == corpus_repo
    known = int(env["PR_NUMBER"]) if in_corpus_repo else None

    pool = await create_pool(env["DATABASE_URL"])
    try:
        async with pool.acquire() as conn:
            repo_id = await conn.fetchval(REPO_SQL, corpus_repo)
            if repo_id is None:
                raise SystemExit(f"{corpus_repo} is not indexed")
            index = await build_bm25_index(conn, repo_id)
            corpus_prs = await conn.fetchval(CORPUS_COUNT_SQL, repo_id)
            await asyncio.to_thread(get_model)
            results = await analyze_diff(
                conn,
                index,
                repo=corpus_repo,
                repo_id=repo_id,
                title=env.get("PR_TITLE", ""),
                body=env.get("PR_BODY"),
                diff=diff,
                known_pr_number=known,
            )
    finally:
        await pool.close()

    if not results:
        print("no comparable code changes: no comment")
        return
    Path(env["COMMENT_PATH"]).write_text(render_comment(results, corpus_repo, corpus_prs))
    print(f"wrote comment with {len(results)} results")


if __name__ == "__main__":
    asyncio.run(run())
