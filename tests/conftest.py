"""Shared fixtures. Each test gets an isolated in-memory database."""
import os
import sys

import pytest

# Ensure src/ is importable without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    """Point each test at its own sqlite file and reset cached singletons."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from career_assistant import config
    from career_assistant.storage import database

    config.get_settings.cache_clear()
    database.get_database.cache_clear()
    yield
    config.get_settings.cache_clear()
    database.get_database.cache_clear()


@pytest.fixture
def profile():
    from career_assistant.models.profile import UserProfile

    return UserProfile(
        user_id="user-1",
        full_name="Test User",
        skills=["python", "fastapi", "docker", "aws"],
        years_experience=4,
        titles=["Backend Engineer"],
        locations_preferred=["Remote"],
        career_goals="Senior backend engineer",
        raw_cv_text="Backend engineer with 4 years experience in python.",
    )
