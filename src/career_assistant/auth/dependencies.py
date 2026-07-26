"""FastAPI auth dependency: resolve the current user from a cookie or Bearer token."""
from __future__ import annotations

from fastapi import HTTPException, Request

from .security import decode_access_token
from ..models.user import User
from ..storage.user_repository import UserRepository
from ..storage.exceptions import DatabaseUnavailable


def get_current_user(request: Request) -> User:
    """Validate token from `careeros_token` cookie or `Authorization: Bearer <jwt>`.

    Raises 401 on any auth problem (missing/invalid/expired token, or unknown user).
    Raises 503 on database unavailability.
    """
    token = None
    authorization = request.headers.get("Authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        token = request.cookies.get("careeros_token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing or malformed authentication credentials")

    claims = decode_access_token(token)
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user = UserRepository().get_by_id(str(claims.get("sub", "")))
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail="Database temporarily unavailable") from exc

    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user
