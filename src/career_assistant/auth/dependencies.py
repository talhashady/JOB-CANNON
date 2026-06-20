"""FastAPI auth dependency: resolve the current user from a Bearer token."""
from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException

from .security import decode_access_token
from ..models.user import User
from ..storage.user_repository import UserRepository


def get_current_user(authorization: Optional[str] = Header(default=None)) -> User:
    """Validate `Authorization: Bearer <jwt>` and return the matching User.

    Raises 401 on any problem (missing/invalid/expired token, or unknown user).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    claims = decode_access_token(token)
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = UserRepository().get_by_id(str(claims.get("sub", "")))
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user
