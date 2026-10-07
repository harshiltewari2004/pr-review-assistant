"""Corpus fingerprint sensitivity. 01 §15, D-P5-9 W2. Pure: no DB."""

from datetime import UTC, datetime

import numpy as np

from eval.snapshot import fingerprint_rows


class _Vec:
    """Stands in for pgvector's Vector: only .to_numpy() is used."""

    def __init__(self, values):
        self._a = np.array(values, dtype=np.float32)

    def to_numpy(self):
        return self._a


def _prs(title="t", in_corpus=True):
    return [
        {
            "id": 1,
            "in_corpus": in_corpus,
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            "title": title,
            "body": None,
            "files_changed": ["src/a.js"],
        }
    ]


def _chunks(x=0.5):
    return [{"id": 10, "pr_id": 1, "embedding": _Vec([x, 0.25])}]


def test_fingerprint_is_deterministic():
    assert fingerprint_rows(_prs(), _chunks()) == fingerprint_rows(_prs(), _chunks())


def test_fingerprint_detects_reembedding():
    # The "unpinned sentence-transformers" case: one float moves.
    assert fingerprint_rows(_prs(), _chunks(0.5)) != fingerprint_rows(_prs(), _chunks(0.5000001))


def test_fingerprint_detects_corpus_filter_change():
    assert fingerprint_rows(_prs(), _chunks()) != fingerprint_rows(_prs(in_corpus=False), _chunks())


def test_fingerprint_detects_text_change():
    # BM25 reads title/body: an edited PR on re-ingest must change it.
    assert fingerprint_rows(_prs(), _chunks()) != fingerprint_rows(_prs(title="t2"), _chunks())
