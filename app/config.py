"""Service settings from the environment (04 §8).

On Cloud Run, secrets arrive as env vars mounted from Secret Manager
(invariant 24); locally, from the shell. A missing secret fails at startup,
loudly, instead of on the first request.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    api_key: str
    repo: str = "processing/p5.js"


@lru_cache
def get_settings() -> Settings:
    return Settings()
