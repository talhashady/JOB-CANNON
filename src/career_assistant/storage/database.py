"""Thin SQLite wrapper.

We deliberately use the stdlib sqlite3 so the project runs with zero external
services. The schema and DAO methods are intentionally simple so a Postgres
backend (psycopg) can be slotted in behind the same repository interface.
"""
from __future__ import annotations

import sqlite3
import threading
from functools import lru_cache
from typing import Optional

from ..config import get_settings
from ..logging_config import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    payload TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    verified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    status TEXT NOT NULL,
    platform TEXT,
    payload TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_apps_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_apps_platform_day
    ON applications(platform, created_at);
"""


class Database:
    """Connection holder with a process-wide lock for write safety."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        log.info("SQLite database ready at %s", path)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, params).fetchall())

    def close(self) -> None:
        self._conn.close()


@lru_cache(maxsize=1)
def get_database(path: Optional[str] = None) -> Database:
    settings = get_settings()
    if not settings.is_sqlite and path is None:
        # Production would branch to a Postgres implementation here.
        log.warning(
            "Non-sqlite DATABASE_URL set (%s) but only the SQLite backend is bundled; "
            "falling back to local sqlite file.",
            settings.database_url,
        )
    return Database(path or settings.sqlite_path)
