"""Environment-driven configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover
    pass


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    try:
        return int(raw) if raw is not None else default
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    try:
        return float(raw) if raw is not None else default
    except ValueError:
        return default


def _list(name: str, default: List[str]) -> List[str]:
    raw = os.environ.get(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    orchestrator_model: str = field(default_factory=lambda: os.environ.get("ORCHESTRATOR_MODEL", "gpt-4o"))
    specialist_model: str = field(default_factory=lambda: os.environ.get("SPECIALIST_MODEL", "gpt-4o-mini"))
    # Gemini (OpenAI-compatible): https://generativelanguage.googleapis.com/v1beta/openai/
    openai_base_url: str = field(default_factory=lambda: os.environ.get("OPENAI_BASE_URL", ""))

    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite:///career_assistant.db"))

    # Auth
    jwt_secret: str = field(default_factory=lambda: os.environ.get("JWT_SECRET", "dev-insecure-secret-change-me"))
    jwt_expire_hours: int = field(default_factory=lambda: _int("JWT_EXPIRE_HOURS", 168))

    allow_live_apply: bool = field(default_factory=lambda: _bool("ALLOW_LIVE_APPLY", False))
    daily_application_cap: int = field(default_factory=lambda: _int("DAILY_APPLICATION_CAP", 20))
    auto_apply_min_score: float = field(default_factory=lambda: _float("AUTO_APPLY_MIN_SCORE", 0.6))

    default_job_sites: List[str] = field(default_factory=lambda: _list("DEFAULT_JOB_SITES", ["indeed"]))
    max_results_per_search: int = field(default_factory=lambda: min(_int("MAX_RESULTS_PER_SEARCH", 50), 1000))

    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def sqlite_path(self) -> str:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return self.database_url[len(prefix):] or ":memory:"
        return ":memory:"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
