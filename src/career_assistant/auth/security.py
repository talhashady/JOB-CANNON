"""Security primitives implemented with the Python standard library only.

Why no external deps: the project must run on a minimal Hugging Face Docker image
with zero surprises. PBKDF2-HMAC-SHA256 (for passwords) and HS256 JWTs (for
sessions) are both available from hashlib/hmac, so we avoid passlib/python-jose.

These are real, production-reasonable implementations - constant-time comparisons,
per-password random salts, and signed+expiring tokens. For very high scale you may
still prefer argon2/bcrypt, but PBKDF2 with a high iteration count is solid.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from ..config import get_settings

_PBKDF2_ITERATIONS = 240_000
_ALGO = "sha256"


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Return an encoded hash: pbkdf2_sha256$iterations$salt_b64$hash_b64."""
    if not password:
        raise ValueError("Password must not be empty.")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(_ALGO, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return "pbkdf2_{algo}${iters}${salt}${hash}".format(
        algo=_ALGO,
        iters=_PBKDF2_ITERATIONS,
        salt=base64.b64encode(salt).decode("ascii"),
        hash=base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verify a password against an encoded hash."""
    try:
        scheme, iters_s, salt_b64, hash_b64 = encoded.split("$")
        if not scheme.startswith("pbkdf2_"):
            return False
        algo = scheme.split("_", 1)[1]
        iters = int(iters_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except Exception:
        return False
    candidate = hashlib.pbkdf2_hmac(algo, password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(candidate, expected)


# --------------------------------------------------------------------------- #
# JWT (HS256) - minimal, dependency-free
# --------------------------------------------------------------------------- #
def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(signing_input: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _b64url_encode(sig)


def create_access_token(subject: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """Create a signed JWT for `subject` (the user id)."""
    settings = get_settings()
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.jwt_expire_hours * 3600,
    }
    if extra:
        payload.update(extra)
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = _sign(signing_input, settings.jwt_secret)
    return f"{header_b64}.{payload_b64}.{signature}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate signature + expiry. Return the claims dict, or None if invalid."""
    settings = get_settings()
    try:
        header_b64, payload_b64, signature = token.split(".")
    except ValueError:
        return None
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = _sign(signing_input, settings.jwt_secret)
    if not hmac.compare_digest(expected_sig, signature):
        return None
    try:
        claims = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None
    if int(claims.get("exp", 0)) < int(time.time()):
        return None
    return claims
