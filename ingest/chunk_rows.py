"""Hunks + vectors → chunk rows. 04 §5 steps 5-6.

A hunk becomes a chunk here (06 §2) — pr_id and repo_id are attached at
persistence, not at parse time (D-P2-19).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.retrieval.chunking import Hunk
from app.retrieval.constants import MAX_MODEL_TOKENS


@dataclass(frozen=True)
class ChunkRow:
    pr_id: int
    repo_id: int
    file_path: str
    hunk_index: int
    content: str
    token_count: int
    was_truncated: bool
    additions: int
    deletions: int
    embedding: np.ndarray

    def as_params(self) -> tuple:
        """Positional order must match INSERT_CHUNK's $1..$10."""
        return (
            self.pr_id,
            self.repo_id,
            self.file_path,
            self.hunk_index,
            self.content,
            self.token_count,
            self.was_truncated,
            self.additions,
            self.deletions,
            self.embedding,
        )


def build_chunk_rows(
    pr_id: int,
    repo_id: int,
    hunks: list[Hunk],
    token_counts: list[int],
    vectors: np.ndarray,
) -> list[ChunkRow]:
    return [
        ChunkRow(
            pr_id=pr_id,
            repo_id=repo_id,
            file_path=h.file_path,
            hunk_index=h.hunk_index,
            content=h.content,
            token_count=tc,
            # TYPE THIS LINE. Invariant 9. Strictly greater: at exactly
            # MAX_MODEL_TOKENS nothing is cut. count_tokens includes
            # [CLS]/[SEP], so both sides count the same thing.
            was_truncated=tc > MAX_MODEL_TOKENS,
            additions=h.additions,
            deletions=h.deletions,
            embedding=v,
        )
        for h, tc, v in zip(hunks, token_counts, vectors, strict=True)
    ]
