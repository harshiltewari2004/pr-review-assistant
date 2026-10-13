"""Request/response models for POST /analyze (04 §4). D-P7-1.

Two deliberate deviations from 04 §4's example:
- The request carries title and body. BM25's document is title + body +
  file basenames (03 §7); without them production would score BM25 on a
  different document than the evaluation did.
- Score fields are *_norm (invariant 6): they are per-query normalized, and
  a bare "vector_score" hides which scale they are on.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

MAX_DIFF_CHARS = 2_000_000  # bounded work per request


class AnalyzeRequest(BaseModel):
    repo: str
    pr_number: int = Field(gt=0)
    title: str = ""
    body: str | None = None
    diff: str = Field(max_length=MAX_DIFF_CHARS)


class AnalyzeResult(BaseModel):
    pr_number: int
    title: str
    url: str
    outcome: str
    final_score: float
    vector_score_norm: float
    file_overlap_score_norm: float
    bm25_score_norm: float
    reason: str


class AnalyzeResponse(BaseModel):
    query_pr: int
    results: list[AnalyzeResult]
