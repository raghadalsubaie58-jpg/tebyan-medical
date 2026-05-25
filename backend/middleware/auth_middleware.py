"""
Supabase JWT verification for FastAPI.

Supabase now supports two signing modes:
  - ES256 (ECDSA, newer projects): verified via JWKS public key endpoint
  - HS256 (HMAC, older projects): verified via SUPABASE_JWT_SECRET

This middleware auto-detects the algorithm from the JWT header and uses
the appropriate verification method.

Usage:
    @app.get("/api/me")
    async def me(user = Depends(require_user)):
        return {"id": user["sub"], "email": user["email"]}

    @app.get("/api/public")
    async def public(user = Depends(optional_user)):
        ...

Environment:
    SUPABASE_URL        — project URL (for JWKS endpoint)
    SUPABASE_JWT_SECRET — required only for HS256 projects
"""

from __future__ import annotations

import os
import logging
import time
from typing import Any

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = logging.getLogger("tebyan.auth")

_JWT_SECRET  = os.getenv("SUPABASE_JWT_SECRET", "")
_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_ALGORITHM_HS = "HS256"
_ALGORITHM_ES = "ES256"
_AUDIENCE     = "authenticated"

# JWKS client — caches public keys for 10 minutes
_jwks_client: PyJWKClient | None = None
_jwks_last_fetched: float = 0.0
_JWKS_CACHE_TTL = 600  # seconds

# auto_error=False lets us handle missing token ourselves (for optional_user)
_bearer = HTTPBearer(auto_error=False)


def _get_jwks_client() -> PyJWKClient | None:
    global _jwks_client, _jwks_last_fetched
    if not _SUPABASE_URL:
        return None
    now = time.time()
    if _jwks_client is None or (now - _jwks_last_fetched) > _JWKS_CACHE_TTL:
        try:
            url = f"{_SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            _jwks_client = PyJWKClient(url, cache_keys=True)
            _jwks_last_fetched = now
            log.debug("JWKS client initialised from %s", url)
        except Exception as e:
            log.warning("Failed to init JWKS client: %s", e)
            return None
    return _jwks_client


def _get_algorithm(token: str) -> str:
    """Peek at the JWT header to determine signing algorithm."""
    try:
        header = jwt.get_unverified_header(token)
        return header.get("alg", _ALGORITHM_HS)
    except Exception:
        return _ALGORITHM_HS


def _decode(token: str) -> dict[str, Any]:
    """
    Decode and verify a Supabase JWT.
    Supports both ES256 (JWKS) and HS256 (secret).
    Raises HTTPException on any failure.
    """
    alg = _get_algorithm(token)

    try:
        if alg == _ALGORITHM_ES:
            # ES256 — verify via JWKS public key
            client = _get_jwks_client()
            if client is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Auth not configured on server (SUPABASE_URL missing)",
                )
            signing_key = client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=[_ALGORITHM_ES],
                audience=_AUDIENCE,
            )
        else:
            # HS256 — verify via shared secret
            if not _JWT_SECRET:
                log.error("SUPABASE_JWT_SECRET not set — cannot verify HS256 tokens")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Auth not configured on server",
                )
            return jwt.decode(
                token,
                _JWT_SECRET,
                algorithms=[_ALGORITHM_HS],
                audience=_AUDIENCE,
            )

    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "session_expired", "message": "انتهت صلاحية الجلسة — يرجى تسجيل الدخول مجدداً"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "رمز المصادقة غير صالح"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        log.debug("JWT decode failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "رمز المصادقة غير صالح"},
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Public dependency functions ───────────────────────────────────────────────

async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """
    FastAPI dependency that returns the decoded JWT payload.
    Raises 401 if the request has no valid Bearer token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing_token", "message": "تسجيل الدخول مطلوب"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode(credentials.credentials)


async def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any] | None:
    """
    FastAPI dependency that returns the decoded JWT payload or None.
    Does not raise — lets the route handle unauthenticated requests.
    Returns None gracefully if JWKS/secret is not configured.
    """
    if not credentials:
        return None
    if not _SUPABASE_URL and not _JWT_SECRET:
        log.debug("Auth not configured — treating request as anonymous")
        return None
    try:
        return _decode(credentials.credentials)
    except HTTPException:
        return None


def get_user_id(user: dict[str, Any]) -> str:
    """Extract the Supabase user UUID from a decoded payload."""
    return user["sub"]


def get_user_email(user: dict[str, Any]) -> str:
    """Extract the user email from a decoded payload."""
    return user.get("email", "")
