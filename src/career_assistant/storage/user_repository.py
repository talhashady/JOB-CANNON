"""User repository (accounts). Same interface style as the other repositories so it
works on both the SQLite and Postgres `Database` backends unchanged.
"""
from __future__ import annotations

from typing import Optional

from ..models.user import User
from .database import Database, get_database


class UserRepository:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def create(self, user: User) -> None:
        self.db.execute(
            "INSERT INTO users (id, email, payload, created_at) VALUES (?, ?, ?, ?)",
            (user.id, user.email.lower(), user.model_dump_json(), user.created_at.isoformat()),
        )

    def get_by_email(self, email: str) -> Optional[User]:
        rows = self.db.query(
            "SELECT payload FROM users WHERE email = ?", (email.strip().lower(),)
        )
        return User.model_validate_json(rows[0]["payload"]) if rows else None

    def get_by_id(self, user_id: str) -> Optional[User]:
        rows = self.db.query("SELECT payload FROM users WHERE id = ?", (user_id,))
        return User.model_validate_json(rows[0]["payload"]) if rows else None

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None
