"""API auth and readiness without DB or model. TestClient is used WITHOUT
`with`, so the lifespan (pool, BM25 index, model) never runs: these tests
check the gate in front of /analyze, not retrieval. D-P7-1.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

BODY = {"repo": "processing/p5.js", "pr_number": 1, "title": "t", "diff": ""}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_analyze_rejects_missing_key(client):
    assert client.post("/analyze", json=BODY).status_code == 401


def test_analyze_rejects_wrong_key(client):
    r = client.post("/analyze", json=BODY, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_health_before_startup_is_not_ready(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is False
