"""Skeleton service. Proves the deployment pipe works (08_setup.md §6).

Real routes land in Phase 3+. Per 04_architecture.md §4 the surface is
three endpoints: GET /health, POST /analyze, GET /similar/{...}.
"""

import os

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    # secrets_loaded reports presence only, never a value — one of the four
    # day-1 failure modes in 08 §6 is "secrets not injected", and the doc's
    # own skeleton cannot detect it.
    return {
        "status": "ok",
        "model_loaded": False,
        "corpus_prs": 0,
        "secrets_loaded": bool(os.getenv("DATABASE_URL")) and bool(os.getenv("API_KEY")),
    }
