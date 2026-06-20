"""Optional PostgreSQL backend - a drop-in replacement for the SQLite `Database`.

Enable it by setting DATABASE_URL to a Postgres connection string (e.g. from a free
Neon or Supabase database):

    DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

Requires:  pip install "psycopg[binary]"   (already added to requirements.txt)

It mirrors the SQLite Database.execute/query interface so the repositories work
unchanged. This codebase writes SQL with '?' placeholders; this adapter rewrites
them to '%s' for psycopg and returns dict rows (so row["col"] keeps working).

Note: created_at columns are TEXT holding ISO timestamps so the cross-database
rate-limit query (substr(created_at,1,10)) behaves identically to SQLite.
"""
from __future__ import annotations

import threading
from typing import Any, List

from ..logging_config import get_logger

log = get_logger(__name__)

_SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        payload TEXT NOT NULL,
        created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    """CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        verified INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text)
    )""",
    """CREATE TABLE IF NOT EXISTS profiles (
        user_id TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        updated_at TEXT DEFAULT (CURRENT_TIMESTAMP::text)
    )""",
    """CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        job_id TEXT NOT NULL,
        status TEXT NOT NULL,
        platform TEXT,
        payload TEXT NOT NULL,
        created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text),
        updated_at TEXT DEFAULT (CURRENT_TIMESTAMP::text)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_apps_user ON applications(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_apps_platform_day ON applications(platform, created_at)",
]


def _translate(sql: str) -> str:
    """Rewrite SQLite-style '?' placeholders to psycopg '%s'."""
    return sql.replace("?", "%s")


class PostgresDatabase:
    """Connection holder mirroring the SQLite Database interface."""

    def __init__(self, dsn: str) -> None:
        import psycopg
        from psycopg.rows import dict_row

        self._psycopg = psycopg
        self._dict_row = dict_row
        self.dsn = dsn
        self._lock = threading.Lock()
        self._conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        with self._conn.cursor() as cur:
            for stmt in _SCHEMA_STATEMENTS:
                cur.execute(stmt)
        log.info("Postgres database ready.")

    def _ensure(self) -> None:
        if self._conn.closed:
            self._conn = self._psycopg.connect(
                self.dsn, autocommit=True, row_factory=self._dict_row
            )

    def execute(self, sql: str, params: tuple = ()) -> Any:
        with self._lock:
            self._ensure()
            with self._conn.cursor() as cur:
                cur.execute(_translate(sql), params)
            return None

    def query(self, sql: str, params: tuple = ()) -> List[dict]:
        with self._lock:
            self._ensure()
            with self._conn.cursor() as cur:
                cur.execute(_translate(sql), params)
                return list(cur.fetchall())

    def close(self) -> None:
        self._conn.close()
