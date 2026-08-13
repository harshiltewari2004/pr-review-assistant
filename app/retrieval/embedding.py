"""Text → 384-dim vectors. Governed by 03_retrieval_engine.md §3.

Lives in app/retrieval/ because both the indexing script and query-time
retrieval embed text. scripts/ may import app/ (D-P2-25); app/ may not
import ingest/, so this cannot live there.

Pure: text in, vectors and token counts out. token_count and was_truncated
are stamped onto chunk rows by the caller (D-P2-19).
"""

from __future__ import annotations

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from app.retrieval.constants import (
    EMBED_BATCH_SIZE,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    MAX_MODEL_TOKENS,
)

log = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Load once. 06 §9 — never per call, never at import time."""
    global _model
    if _model is None:
        log.info("loading %s", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL)

        # ---- READ THIS ONE ----
        # The model's own limit must agree with the constant the corpus-wide
        # truncation rate is computed against. If a version bump moves
        # max_seq_length, every was_truncated in the database is wrong and
        # nothing raises. Fail at load instead.
        if _model.max_seq_length != MAX_MODEL_TOKENS:
            raise RuntimeError(
                f"model max_seq_length {_model.max_seq_length} "
                f"!= MAX_MODEL_TOKENS {MAX_MODEL_TOKENS}"
            )
        if _model.get_sentence_embedding_dimension() != EMBEDDING_DIM:
            raise RuntimeError("model dimension does not match EMBEDDING_DIM")
    return _model


def count_tokens(texts: list[str]) -> list[int]:
    """True token length, including [CLS]/[SEP], before any truncation.

    truncation=False is the point of this function: the model would silently
    cut at MAX_MODEL_TOKENS, and a count taken after that is always <= the
    limit, which makes was_truncated permanently False.
    """
    tokenizer = get_model().tokenizer
    encoded = tokenizer(
        texts,
        add_special_tokens=True,
        truncation=False,
        padding=False,
        verbose=False,  # suppresses the per-call over-length warning
    )
    return [len(ids) for ids in encoded["input_ids"]]


def embed(texts: list[str]) -> np.ndarray:
    """(len(texts), 384) float32, unit-normalized."""
    if not texts:
        return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

    # ---- READ THIS ONE ----
    # normalize_embeddings=True is NOT what makes <=> cosine — pgvector
    # divides by both norms itself and returns identical rankings either
    # way (confirmed by the day-3 spike). What it buys is agreement
    # OUTSIDE Postgres: on unit vectors, 1 - (a <=> b) equals a plain dot
    # product, so numpy, a spike script, and <#> all rank the same way.
    # Unnormalized they disagree, and the disagreement is silent. 03 §3.
    vectors = get_model().encode(
        texts,
        normalize_embeddings=True,
        batch_size=EMBED_BATCH_SIZE,
        show_progress_bar=False,
    )
    return vectors.astype(np.float32)