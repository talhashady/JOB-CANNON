"""Account models for authentication.

Email is validated with a lightweight regex (no `email-validator` dependency) so the
backend stays dependency-light and import-safe on a minimal Docker image.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _validate_email(value: str) -> str:
    v = (value or "").strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("Invalid email address")
    return v


class User(BaseModel):
    """A registered account. `password_hash` never leaves the backend."""

    id: str
    email: str
    full_name: str = ""
    password_hash: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)

    def public(self) -> "PublicUser":
        return PublicUser(
            id=self.id, email=self.email, full_name=self.full_name, created_at=self.created_at
        )


class PublicUser(BaseModel):
    """Safe user view returned to clients (no secrets)."""

    id: str
    email: str
    full_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SignupRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = ""

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: PublicUser
