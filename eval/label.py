"""Blind labeling CLI. 01 §10, 02 §7. D-P5-10, D-P5-11.

Usage:
    python -m eval.label --batch 1 --plan   # batch composition; writes nothing
    python -m eval.label --batch 1          # label (resumable: q to quit)

Blind: candidates shuffled per query; no score, rank, variant, or author is
shown, and the query's own outcome is hidden (future information). Round 1
only, plain INSERT: a duplicate raises rather than overwriting (invariant 15).
Skips are final, logged to skips.jsonl, capped at 5% (01 §10).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from ingest.db import connect

ARTIFACTS = Path(__file__).parent / "artifacts"
POOL_PATH = ARTIFACTS / "pool.json"
SKIPS_PATH = ARTIFACTS / "skips.jsonl"

LABELER_LOGIN = "harshiltewari2004"  # D-P5-10
PR_URL = "https://github.com/processing/p5.js/pull"
ROUND = 1
MAX_REASON_WORDS = 6  # 01 §10
SKIP_CAP = 0.05  # 01 §10
TIME_BOX_S = 45  # 01 §10
BODY_CHARS = 700
FILES_SHOWN = 12

OUTCOME_TEXT = {
    "merged": "merged",
    "closed_unmerged": "closed without merging",  # invariant 17
    "open": "open",
}

RUBRIC = """\
Without having seen the CANDIDATE, would the QUERY's reviewer review worse?
  2  strongly related, and you can name how: they would miss a known
     failure mode / re-litigate a settled design debate / duplicate (or
     repeat abandoned) work
  1  related: same subsystem or concern, no nameable consequence
  0  unrelated
  s  skip (final, capped at 5%)    q  quit (resumable)
Reason required for 1 and 2, six words or fewer. Can't write one -> downgrade."""

QUERIES_SQL = "SELECT pr_id, split, subsystem FROM eval_queries"
PR_SQL = """
SELECT id, number, title, body, outcome, files_changed, additions, deletions, author
FROM pull_requests WHERE id = ANY($1::bigint[])
"""
DONE_SQL = "SELECT query_pr_id, candidate_pr_id FROM judgments WHERE round = $1"
INSERT_SQL = """
INSERT INTO judgments
    (query_pr_id, candidate_pr_id, grade, reason, round, batch, seconds_spent, self_authored)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
"""
BATCH_STATS_SQL = """
SELECT count(*) AS n, array_agg(seconds_spent) AS secs
FROM judgments WHERE round = $1 AND batch = $2
"""


def batch_query_ids(rows, batch: int) -> list[int]:
    """D-P5-11: per split, sort by (subsystem, pr_id); batch 1 = even positions."""
    chosen: list[int] = []
    for split in ("tune", "holdout"):
        ordered = sorted(
            (r for r in rows if r["split"] == split),
            key=lambda r: (r["subsystem"], r["pr_id"]),
        )
        chosen += [r["pr_id"] for r in ordered[batch - 1 :: 2]]
    return chosen


def load_skips() -> set[tuple[int, int]]:
    if not SKIPS_PATH.exists():
        return set()
    lines = SKIPS_PATH.read_text().splitlines()
    return {(s["query_pr_id"], s["candidate_pr_id"]) for s in map(json.loads, lines) if s}


def record_skip(query_pr_id: int, candidate_pr_id: int, batch: int) -> None:
    entry = {
        "query_pr_id": query_pr_id,
        "candidate_pr_id": candidate_pr_id,
        "batch": batch,
        "at": datetime.now(UTC).isoformat(),
    }
    with SKIPS_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def render(pr, role: str, show_outcome: bool) -> str:
    files = pr["files_changed"]
    listed = "\n".join(f"    {f}" for f in files[:FILES_SHOWN])
    if len(files) > FILES_SHOWN:
        listed += f"\n    ... +{len(files) - FILES_SHOWN} more"
    # PR templates wrap their instructions in <!-- -->; GitHub never renders
    # them, so neither do we. Without this, boilerplate eats BODY_CHARS.
    body = re.sub(r"<!--.*?-->", "", pr["body"] or "", flags=re.DOTALL).strip()
    body = body or "(no description)"
    if len(body) > BODY_CHARS:
        body = body[:BODY_CHARS] + " [...]"
    outcome = f"  [{OUTCOME_TEXT[pr['outcome']]}]" if show_outcome else ""
    return (
        f"{role} #{pr['number']}{outcome}  +{pr['additions']} -{pr['deletions']}\n"
        f"  {pr['title']}\n"
        f"  {PR_URL}/{pr['number']}\n"
        f"  files ({len(files)}):\n{listed}\n"
        f"  {body}"
    )


def ask_grade() -> str:
    while True:
        answer = input("grade [0/1/2/s/q]: ").strip().lower()
        if answer in {"0", "1", "2", "s", "q"}:
            return answer


def ask_reason() -> str:
    while True:
        reason = input(f"reason (<= {MAX_REASON_WORDS} words): ").strip()
        words = len(reason.split())
        if 1 <= words <= MAX_REASON_WORDS:
            return reason
        print(f"  need 1-{MAX_REASON_WORDS} words, got {words}")


async def print_summary(conn, batch: int, total: int) -> None:
    stats = await conn.fetchrow(BATCH_STATS_SQL, ROUND, batch)
    secs = [s for s in (stats["secs"] or []) if s is not None]
    skips = sum(1 for _, _, b in _skip_batches() if b == batch)
    rate = skips / total if total else 0.0
    median = statistics.median(secs) if secs else 0
    print(
        f"\nbatch {batch}: judged {stats['n']}/{total}, skipped {skips} "
        f"({rate:.1%}), median {median:.0f}s/judgment"
    )
    if rate > SKIP_CAP:
        print(f"  WARNING: skip rate above {SKIP_CAP:.0%} cap (01 §10) — fix queries, not rubric")


def _skip_batches():
    if not SKIPS_PATH.exists():
        return []
    rows = [json.loads(line) for line in SKIPS_PATH.read_text().splitlines() if line]
    return [(r["query_pr_id"], r["candidate_pr_id"], r["batch"]) for r in rows]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Blind labeling CLI (01 §10)")
    parser.add_argument("--batch", type=int, choices=(1, 2), required=True)
    parser.add_argument("--plan", action="store_true", help="show batch, write nothing")
    args = parser.parse_args()

    pool = {
        e["query_pr_id"]: e["candidate_pr_ids"]
        for e in json.loads(POOL_PATH.read_text())["queries"]
    }

    async with connect("local") as conn:
        qrows = await conn.fetch(QUERIES_SQL)
        assert len(qrows) == 20, f"expected 20 eval queries, got {len(qrows)}"
        meta = {r["pr_id"]: r for r in qrows}
        batch_ids = batch_query_ids(qrows, args.batch)
        assert len(batch_ids) == 10, batch_ids
        assert sum(meta[q]["split"] == "tune" for q in batch_ids) == 5, "D-P5-11: 5 tune"

        all_ids = set(batch_ids) | {c for q in batch_ids for c in pool[q]}
        prs = {r["id"]: r for r in await conn.fetch(PR_SQL, list(all_ids))}
        assert len(prs) == len(all_ids), "pool references a missing PR"

        done = {(r["query_pr_id"], r["candidate_pr_id"]) for r in await conn.fetch(DONE_SQL, ROUND)}
        skipped = load_skips()
        pairs = [(q, c) for q in batch_ids for c in pool[q]]
        total = len(pairs)

        if args.plan:
            for q in batch_ids:
                m = meta[q]
                print(
                    f"#{prs[q]['number']:<5} {m['split']:<7} {m['subsystem']:<10} "
                    f"pool={len(pool[q])}"
                )
            remaining = sum(1 for p in pairs if p not in done and p not in skipped)
            print(f"\nbatch {args.batch}: {total} pairs, {remaining} remaining")
            return

        print(RUBRIC)
        for qi, q in enumerate(batch_ids, 1):
            todo = [c for c in pool[q] if (q, c) not in done and (q, c) not in skipped]
            if not todo:
                continue
            random.shuffle(todo)
            print("\n" + "=" * 78)
            print(f"QUERY {qi}/10\n" + render(prs[q], "QUERY", show_outcome=False))

            for ci, c in enumerate(todo, 1):
                print("\n" + "-" * 78)
                print(f"query #{prs[q]['number']}: {prs[q]['title']}")
                print(f"candidate {ci}/{len(todo)}\n" + render(prs[c], "CANDIDATE", True))
                started = time.monotonic()

                while True:
                    answer = ask_grade()
                    if answer == "q":
                        await print_summary(conn, args.batch, total)
                        return
                    if answer == "s":
                        break
                    grade = int(answer)
                    reason = ask_reason() if grade > 0 else None
                    shown = f"{grade}" + (f" — {reason}" if reason else "")
                    if input(f"save {shown}? [Enter=save / r=redo]: ").strip().lower() != "r":
                        break

                if answer == "s":
                    record_skip(q, c, args.batch)
                    continue

                seconds = round(time.monotonic() - started)
                self_authored = LABELER_LOGIN in (prs[q]["author"], prs[c]["author"])
                await conn.execute(
                    INSERT_SQL, q, c, grade, reason, ROUND, args.batch, seconds, self_authored
                )
                if seconds > 2 * TIME_BOX_S:
                    print(f"  ({seconds}s — over 2x the {TIME_BOX_S}s box)")

        await print_summary(conn, args.batch, total)


if __name__ == "__main__":
    asyncio.run(main())
