"""Thin SQLite wrapper.

We deliberately use the stdlib sqlite3 so the project runs with zero external
services. The schema and DAO methods are intentionally simple so a Postgres
backend (psycopg) can be slotted in behind the same repository interface.
"""
from __future__ import annotations

import sqlite3
import threading
from typing import Any, Optional

from ..config import get_settings
from ..logging_config import get_logger
from .exceptions import DatabaseUnavailable

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


# In-memory cache for the Postgres connection. If Postgres fails, it is set to None
# and re-attempted on subsequent calls, fulfilling connection recovery.
_postgres_db: Optional[Any] = None
_db_lock = threading.Lock()

# Startup SQLite warning logging flag
_logged_sqlite_warning = False


def get_database(path: Optional[str] = None) -> Any:
    global _postgres_db, _logged_sqlite_warning
    settings = get_settings()

    # If SQLite configured or custom path specified, use local SQLite
    if settings.is_sqlite or path is not None:
        if not _logged_sqlite_warning and path is None:
            log.warning("No Postgres DATABASE_URL configured. Running in local/dev mode with SQLite database.")
            _logged_sqlite_warning = True
        return Database(path or settings.sqlite_path)

    # Postgres is configured - do NOT silently fallback to SQLite
    with _db_lock:
        if _postgres_db is not None:
            try:
                # Ensure connection is active and healthy
                _postgres_db._ensure()
                return _postgres_db
            except Exception as exc:
                log.warning("Existing Postgres connection failed health check. Retrying connection. Error: %s", exc)
                try:
                    _postgres_db.close()
                except Exception:
                    pass
                _postgres_db = None

        # Attempt to establish new connection to Postgres
        try:
            from .postgres import PostgresDatabase
            db = PostgresDatabase(settings.database_url)
            _postgres_db = db
            return db
        except Exception as exc:
            log.error("Failed to connect to Postgres: %s", exc)
            raise DatabaseUnavailable("Database temporarily unavailable") from exc
