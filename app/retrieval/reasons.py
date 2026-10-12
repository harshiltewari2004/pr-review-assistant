"""Template reason strings for the top-3 results. 03 §10. D-P4-11, D-P4-15.

Template-based, never LLM-generated (invariant 18): the same inputs always
give the same comment. First matching rule wins. Thresholds compare the
per-query NORMALIZED scores (ScoredCandidate.*_score_norm), never raw ones
(D-P4-11). Closed-unmerged candidates say "closed without merging", never
"rejected" (invariant 17).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from app.retrieval.constants import (
    CLOSED_UNMERGED_SUFFIX,
    REASON_BM25_NORM_HIGH,
    REASON_TOP_TERMS,
    REASON_VECTOR_NORM_HIGH,
)
from app.retrieval.signals import Bm25Index, build_document

if TYPE_CHECKING:
    from app.retrieval.scoring import ScoredCandidate

OUTCOMES = ("merged", "closed_unmerged", "open")  # 02 §4; never "rejected"
CANDIDATE_ROWS_SQL = """
SELECT id, title, body, files_changed, outcome
FROM pull_requests WHERE id = ANY($1::bigint[])
"""


def shared_file(query_files: Sequence[str], candidate_files: Sequence[str]) -> str | None:
    """A file both PRs change, or None. Alphabetically first, so output is deterministic."""
    shared = sorted(set(query_files) & set(candidate_files))
    return shared[0] if shared else None


def _shared_depth(a: str, b: str) -> int:
    """How many leading directories two file paths have in common."""
    depth = 0
    for x, y in zip(PurePosixPath(a).parent.parts, PurePosixPath(b).parent.parts, strict=False):
        if x != y:
            break
        depth += 1
    return depth


def closest_file(query_files: Sequence[str], candidate_files: Sequence[str]) -> str:
    """The candidate file nearest the query's files by shared directory depth. D-P4-15.

    Approximates "their top file" for rule 3: VectorAggregate carries no
    per-chunk file, and changing the vector SQL would touch locked numbers.
    Ties go to the alphabetically first file.
    """
    return max(
        sorted(candidate_files),
        key=lambda f: max((_shared_depth(f, q) for q in query_files), default=0),
    )


def top_directory(path: str) -> str:
    """'src/webgl/p5.RendererGL.js' -> 'src/webgl'. Up to two directory levels."""
    parts = PurePosixPath(path).parent.parts
    return "/".join(parts[:2]) if parts else "the repository root"


def top_matched_terms(
    query_tokens: Sequence[str],
    candidate_tokens: Sequence[str],
    idf: Mapping[str, float],
    n: int = REASON_TOP_TERMS,
) -> list[str]:
    """The n shared terms with the highest IDF (rarest first); ties alphabetical."""
    shared = set(query_tokens) & set(candidate_tokens)
    return sorted(shared, key=lambda t: (-idf.get(t, 0.0), t))[:n]


def build_reason(
    *,
    vector_norm: float,
    bm25_norm: float,
    query_files: Sequence[str],
    candidate_files: Sequence[str],
    matched_terms: Sequence[str],
    outcome: str,
) -> str:
    """03 §10 rule chain, first match wins, plus the closed-unmerged suffix."""
    assert candidate_files, "an in-corpus PR always changes at least one file"
    assert outcome in OUTCOMES, f"unknown outcome {outcome!r}"

    shared = shared_file(query_files, candidate_files)
    if shared and vector_norm > REASON_VECTOR_NORM_HIGH:
        text = f"Both modify {shared} with a similar change pattern"
    elif shared:
        text = f"Also changes {shared}"
    elif vector_norm > REASON_VECTOR_NORM_HIGH:
        text = f"Similar change pattern in {closest_file(query_files, candidate_files)}"
    elif bm25_norm > REASON_BM25_NORM_HIGH and matched_terms:
        text = f"Shares terminology: {', '.join(matched_terms)}"
    else:
        text = f"Related change in {top_directory(closest_file(query_files, candidate_files))}"

    if outcome == "closed_unmerged":
        text += CLOSED_UNMERGED_SUFFIX
    return text


async def explain(
    conn,
    index: Bm25Index,
    *,
    query_files: Sequence[str],
    query_tokens: Sequence[str],
    results: Sequence[ScoredCandidate],
) -> list[str]:
    """One reason per ranked result, in the same order. This module's only I/O."""
    if not results:
        return []
    fetched = await conn.fetch(CANDIDATE_ROWS_SQL, [r.pr_id for r in results])
    rows = {row["id"]: row for row in fetched}
    assert len(rows) == len(results), "a ranked result has no pull_requests row"

    reasons = []
    for r in results:
        row = rows[r.pr_id]
        tokens = build_document(row["title"], row["body"], row["files_changed"])
        reasons.append(
            build_reason(
                vector_norm=r.vector_score_norm,
                bm25_norm=r.bm25_score_norm,
                query_files=query_files,
                candidate_files=row["files_changed"],
                matched_terms=top_matched_terms(query_tokens, tokens, index.bm25.idf),
                outcome=row["outcome"],
            )
        )
    return reasons
