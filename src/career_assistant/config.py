"""Environment-driven configuration.

Kept dependency-light on purpose: a dataclass + os.environ + optional dotenv. This
means config has no hard dependency on pydantic-settings and is trivial to test.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List

try:  # optional: load a local .env if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
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
    """Immutable application settings resolved from the environment."""

    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    # Defaults target Google's Gemma 4 31B (model id 'gemma-4-31b-it') served via the
    # Gemini API's OpenAI-compatible endpoint. Override per-deployment via env if needed.
    orchestrator_model: str = field(default_factory=lambda: os.environ.get("ORCHESTRATOR_MODEL", "gemma-4-31b-it"))
    specialist_model: str = field(default_factory=lambda: os.environ.get("SPECIALIST_MODEL", "gemma-4-31b-it"))
    # Point the OpenAI-compatible client at the provider. For Gemma/Gemini you MUST set:
    #   OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    # Leave empty only when using real OpenAI models.
    openai_base_url: str = field(default_factory=lambda: os.environ.get("OPENAI_BASE_URL", ""))

    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite:///career_assistant.db"))

    # --- Auth ---
    jwt_secret: str = field(default_factory=lambda: os.environ.get("JWT_SECRET", "dev-insecure-secret-change-me"))
    jwt_expire_hours: int = field(default_factory=lambda: _int("JWT_EXPIRE_HOURS", 168))

    allow_live_apply: bool = field(default_factory=lambda: _bool("ALLOW_LIVE_APPLY", False))
    # Per-platform applications allowed per day. Raised to support high-volume
    # campaigns (50+/day). Each job board counts separately.
    daily_application_cap: int = field(default_factory=lambda: _int("DAILY_APPLICATION_CAP", 75))
    # Default minimum match score (0..1) required before auto-apply submits.
    auto_apply_min_score: float = field(default_factory=lambda: _float("AUTO_APPLY_MIN_SCORE", 0.6))

    default_job_sites: List[str] = field(default_factory=lambda: _list("DEFAULT_JOB_SITES", ["indeed"]))
    max_results_per_search: int = field(default_factory=lambda: min(_int("MAX_RESULTS_PER_SEARCH", 250), 1000))

    # --- LLM rate limiting (prevents Gemini/OpenAI 429 "quota exceeded" storms) ---
    # Minimum seconds between LLM calls, process-wide. Free Gemini tiers allow very
    # few requests/min (and as low as 20/day on some models), so spacing calls out
    # avoids hammering the API with retries. Set e.g. 4.0 on a free key.
    llm_min_interval_s: float = field(default_factory=lambda: _float("LLM_MIN_INTERVAL_S", 0.0))
    # How many times the OpenAI client retries a 429/5xx before giving up.
    llm_max_retries: int = field(default_factory=lambda: _int("LLM_MAX_RETRIES", 5))

    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))

    @property
    def llm_enabled(self) -> bool:
        """True when a real LLM should be used; otherwise deterministic fallbacks run."""
        return bool(self.openai_api_key)

    @property
    def sqlite_path(self) -> str:
        """Filesystem path for a sqlite:/// URL (':memory:' supported)."""
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return self.database_url[len(prefix):] or ":memory:"
        return ":memory:"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
