"""Select the 20 evaluation query PRs. 01 §8, §13; 02 §6; D-P5-2 reopened Day 28.

Dry run by default: prints the draw. --write inserts into eval_queries, once.
"""

from __future__ import annotations

import argparse
import asyncio
import bisect
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from app.retrieval.constants import BM25_TOP_K, FILE_OVERLAP_TOP_K, VECTOR_TOP_K
from eval.snapshot import corpus_fingerprint
from ingest.db import connect

REPO = "processing/p5.js"
N_QUERIES = 20
SEED = 28  # Fixed before the first draw. Never changed after seeing it.

# Order matters: 1.x FES lives INSIDE src/core/, so fes must match before core.
STRATA: list[tuple[str, tuple[str, ...]]] = [
    ("fes", ("src/core/friendly_errors/", "src/friendly_errors/")),
    ("core", ("src/core/",)),
    ("webgl", ("src/webgl/", "src/3d/")),
    ("strands", ("src/strands/",)),
    ("image", ("src/image/",)),
    ("math", ("src/math/",)),
    ("typography", ("src/typography/", "src/type/")),
]

# Fewer past PRs than the largest possible candidate set means retrieval
# degenerates to ranking the whole past. 03 §4.
MIN_PAST_PRS = VECTOR_TOP_K + FILE_OVERLAP_TOP_K + BM25_TOP_K

# A changed line starting with one of these is a comment. p5.js keeps its
# reference docs as JSDoc inside src/, so without this, doc edits count as
# code changes. 01 §8 requires genuine code-change queries.
COMMENT_PREFIXES = ("*", "//", "/*")

# PRs the pipeline was developed against (spikes, fixtures, golden
# assertions). Applied AFTER the shuffle, so a late addition only moves the
# next PR in line up instead of re-drawing the stratum.
# 6922: studied in DECISIONS.md L1361/L1372; in_corpus is an open item there.
EXCLUDED_NUMBERS: frozenset[int] = frozenset({8994, 6922})

# Drawn but unreadable -> next in line. Reason required. Also post-shuffle.
# Never replace because of retrieval output: none has been run on these.
REPLACED: dict[int, str] = {}

# --- v1.1 continuation (D-V11-1) ---------------------------------------------
# 01 §7 rubric anchors (queries and candidates): known in detail, never queries.
ANCHOR_NUMBERS: frozenset[int] = frozenset(
    {8933, 8994, 8829, 8590, 4378, 8809, 8259, 6222, 8821, 8862, 8964}
)
# Any PR number appearing here was studied during development (D-V11-1).
CONTAMINATION_PATHS = ("tests", "scripts", "JOURNAL.md", "DECISIONS.md", "frontend")
_PR_NUMBER = re.compile(r'#(\d{1,5})\b|/pull/(\d{1,5})\b|"(?:pr_number|number)":\s*(\d{1,5})')
ROOT = Path(__file__).resolve().parent.parent
POOL_PATH = ROOT / "eval" / "artifacts" / "pool.json"  # holds the v1.0 fingerprint


def contamination_numbers() -> set[int]:
    """PR numbers mentioned anywhere under CONTAMINATION_PATHS. D-V11-1."""
    found: set[int] = set()
    for name in CONTAMINATION_PATHS:
        base = ROOT / name
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for path in files:
            if "__pycache__" in path.parts or path.suffix in {".png", ".pyc"}:
                continue
            for m in _PR_NUMBER.finditer(path.read_text(errors="ignore")):
                found.add(int(next(g for g in m.groups() if g)))
    return found


PRS_SQL = """
SELECT pr.id, pr.number, pr.title, pr.created_at
FROM pull_requests pr JOIN repos r ON r.id = pr.repo_id
WHERE r.full_name = $1 AND pr.in_corpus
ORDER BY pr.created_at, pr.id
"""

CHUNKS_SQL = """
SELECT c.pr_id, c.file_path, c.content
FROM chunks c
JOIN pull_requests pr ON pr.id = c.pr_id
JOIN repos r ON r.id = pr.repo_id
WHERE r.full_name = $1 AND pr.in_corpus
"""


def _normalize(code: str) -> str:
    """Strip what a formatter changes: whitespace, quote style, semicolons,
    trailing commas before a closing bracket."""
    code = re.sub(r"\s+", "", code).replace('"', "'").replace(";", "")
    return re.sub(r",(?=[)\]}])", "", code)


def changes_code(content: str) -> bool:
    """True if the chunk changes non-comment code beyond formatting.

    Removed and added code lines are joined BEFORE normalizing, so a line
    reflowed across several lines compares equal to the original.
    """
    removed: list[str] = []
    added: list[str] = []
    for line in content.splitlines():
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        body = line[1:].strip()
        if body and not body.startswith(COMMENT_PREFIXES):
            (added if line[0] == "+" else removed).append(body)
    return _normalize("".join(removed)) != _normalize("".join(added))


def stratum_of(path: str) -> str | None:
    """Stratum for one file path; 'other:<dir>' for unmapped src dirs."""
    for name, prefixes in STRATA:
        if path.startswith(prefixes):
            return name
    if path.startswith("src/") and path.count("/") >= 2:
        return "other:" + path.split("/")[1]
    return None  # tests, docs, build: no subsystem


def dominant_stratum(paths: list[str]) -> str | None:
    """Stratum with the most code chunks. Ties and unmapped winners -> None."""
    counts = Counter(s for p in paths if (s := stratum_of(p)))
    if not counts:
        return None
    ranked = counts.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    top = ranked[0][0]
    return None if top.startswith("other:") else top


async def main(write: bool, cohort: str) -> None:
    async with connect("local") as conn:
        skip: set[int] = set()
        new_rows: list[tuple[str, str, object]] = []
        if cohort == "v1.1":
            repo_id = await conn.fetchval("SELECT id FROM repos WHERE full_name = $1", REPO)
            v10 = json.loads(POOL_PATH.read_text())["corpus_fingerprint"]
            if await corpus_fingerprint(conn, repo_id) != v10:
                raise SystemExit("v1.1 queries are drawn on the v1.0 corpus (D-V11-1)")
            skip = set(ANCHOR_NUMBERS) | contamination_numbers()

        prs = await conn.fetch(PRS_SQL, REPO)
        chunk_rows = await conn.fetch(CHUNKS_SQL, REPO)

        # Only code-changing chunks decide a PR's subsystem.
        code_paths: dict[int, list[str]] = defaultdict(list)
        for row in chunk_rows:
            if changes_code(row["content"]):
                code_paths[row["pr_id"]].append(row["file_path"])

        created = [pr["created_at"] for pr in prs]
        pools: dict[str, list] = defaultdict(list)
        for pr in prs:
            past = bisect.bisect_left(created, pr["created_at"])  # strictly earlier
            stratum = dominant_stratum(code_paths.get(pr["id"], []))
            if stratum and past >= MIN_PAST_PRS:
                pools[stratum].append(pr)

        # Allocation: smallest pools get the floor, the rest get one more.
        names = [name for name, _ in STRATA]
        base, extra = divmod(N_QUERIES, len(names))
        by_size = sorted(names, key=lambda s: (len(pools[s]), s))
        k = {s: base for s in names}
        for s in by_size[len(names) - extra :]:
            k[s] += 1

        rng = random.Random(SEED)
        chosen: list[tuple[str, str, object]] = []
        tune_gets_extra = True
        for s in names:
            order = sorted(pools[s], key=lambda pr: pr["number"])
            rng.shuffle(order)
            order = [
                pr
                for pr in order
                if pr["number"] not in EXCLUDED_NUMBERS and pr["number"] not in REPLACED
            ]
            picked, next_up = order[: k[s]], order[k[s] : k[s] + 3]

            rng.shuffle(picked)
            n_tune = len(picked) // 2
            if len(picked) % 2:
                n_tune += tune_gets_extra
                tune_gets_extra = not tune_gets_extra

            print(f"\n== {s}: eligible={len(pools[s])} k={k[s]}")
            for i, pr in enumerate(picked):
                split = "tune" if i < n_tune else "holdout"
                chosen.append((s, split, pr))
                print(f"  #{pr['number']:<6} {split:<8} {pr['title'][:70]}")
            print("  next in line:", [f"#{pr['number']}" for pr in next_up])

            # D-V11-1: continue the SAME shuffled list. No extra RNG calls here,
            # so later strata see exactly the RNG state v1.0 saw.
            if cohort == "v1.1":
                cont = []
                for pr in order[k[s] :]:
                    if pr["number"] in skip:
                        print(f"  v1.1 skip #{pr['number']}: anchor or mentioned in repo")
                        continue
                    cont.append(pr)
                    if len(cont) == k[s]:
                        break
                assert len(cont) == k[s], (s, len(cont))
                for pr in cont:
                    new_rows.append((s, "holdout", pr))
                    print(f"  v1.1 #{pr['number']:<6} holdout  {pr['title'][:70]}")

        splits = Counter(split for _, split, _ in chosen)
        assert len(chosen) == N_QUERIES, len(chosen)
        assert splits["tune"] == splits["holdout"] == N_QUERIES // 2, splits
        assert len({s for s, _, _ in chosen}) >= 6  # 01 §8
        print(f"\nsplits: {dict(splits)}   replaced: {REPLACED or 'none'}")

        if cohort == "v1.1":
            v10_rows = await conn.fetch("SELECT pr_id FROM eval_queries WHERE cohort = 'v1.0'")
            existing = {r["pr_id"] for r in v10_rows}
            reproduced = {pr["id"] for _, _, pr in chosen}
            assert reproduced == existing, "v1.0 draw not reproduced: RNG state diverged"
            assert len(new_rows) == N_QUERIES, len(new_rows)
            assert not ({pr["id"] for _, _, pr in new_rows} & existing)
            print(f"v1.1: {len(new_rows)} new holdout queries; v1.0 draw reproduced exactly")
            if not write:
                print("dry run — nothing written")
                return
            if await conn.fetchval("SELECT count(*) FROM eval_queries WHERE cohort = 'v1.1'"):
                raise SystemExit("v1.1 queries already written (D-V11-1)")
            async with conn.transaction():
                await conn.executemany(
                    "INSERT INTO eval_queries (pr_id, subsystem, split, cohort) "
                    "VALUES ($1, $2, $3, 'v1.1')",
                    [(pr["id"], s, split) for s, split, pr in new_rows],
                )
            print(f"wrote {len(new_rows)} v1.1 rows to eval_queries")
            return

        if not write:
            print("dry run — nothing written")
            return

        if await conn.fetchval("SELECT count(*) FROM eval_queries WHERE cohort = 'v1.0'"):
            raise SystemExit("eval_queries is not empty — the split is fixed once (02 §6)")
        async with conn.transaction():
            await conn.executemany(
                "INSERT INTO eval_queries (pr_id, subsystem, split) VALUES ($1, $2, $3)",
                [(pr["id"], s, split) for s, split, pr in chosen],
            )
        print(f"wrote {len(chosen)} rows to eval_queries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--cohort", choices=("v1.0", "v1.1"), default="v1.0")
    args = parser.parse_args()
    asyncio.run(main(args.write, args.cohort))
