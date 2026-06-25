"""Authentication: JWT bearer tokens + API key support.

A request is authorised if it carries EITHER:
  - a valid `Authorization: Bearer <jwt>` header, OR
  - a valid `X-API-Key: <key>` header.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


# --------------------------------------------------------------------------- #
# JWT helpers
# --------------------------------------------------------------------------- #
def create_access_token(subject: str) -> tuple[str, int]:
    """Create a signed JWT. Returns (token, expires_in_seconds)."""
    expire_seconds = settings.jwt_expire_minutes * 60
    payload = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expire_seconds),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expire_seconds


def verify_credentials(username: str, password: str) -> bool:
    """Constant-time check of the demo admin credentials."""
    user_ok = secrets.compare_digest(username, settings.admin_username)
    pass_ok = secrets.compare_digest(password, settings.admin_password)
    return user_ok and pass_ok


def _decode_jwt(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def _valid_api_key(api_key: str) -> bool:
    for key in settings.api_key_list:
        if secrets.compare_digest(api_key, key):
            return True
    return False


# --------------------------------------------------------------------------- #
# FastAPI dependency
# --------------------------------------------------------------------------- #
async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> str:
    """Authorise a request via JWT or API key. Returns the principal identity."""
    if credentials and credentials.scheme.lower() == "bearer":
        subject = _decode_jwt(credentials.credentials)
        if subject:
            return subject

    if x_api_key and _valid_api_key(x_api_key):
        return f"apikey:{x_api_key[:4]}***"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid credentials. Provide a Bearer token or X-API-Key.",
        headers={"WWW-Authenticate": "Bearer"},
    )
