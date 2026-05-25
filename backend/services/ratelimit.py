"""
Rate limiter for FastAPI — Redis-backed in production, in-memory fallback.

Redis mode: works correctly across multiple uvicorn workers.
Memory mode: single-process only (development / single-worker deploys).

Env vars:
  REDIS_URL — e.g. "redis://redis:6379/0" (enables Redis mode)
              If unset, falls back to in-memory sliding window.
"""
from __future__ import annotations

import os
import time
import logging
import threading
from collections import defaultdict, deque

from fastapi import Request, HTTPException

log = logging.getLogger("tebyan.ratelimit")

_REDIS_URL   = os.getenv("REDIS_URL", "")
_IS_PROD     = os.getenv("ENVIRONMENT", "development") == "production"
_TRUSTED_PROXY = os.getenv("TRUSTED_PROXY_IPS", "").split(",")


def _extract_ip(request: Request) -> str:
    """Return real client IP. Only trust X-Forwarded-For in production behind nginx."""
    if _IS_PROD:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Redis-backed limiter ────────────────────────────────────────────────────

class _RedisLimiter:
    """
    Sliding-window rate limiter backed by Redis sorted sets.
    Works correctly with multiple uvicorn workers.
    """

    def __init__(self, redis_url: str) -> None:
        import redis as _redis
        self._r = _redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        self._r.ping()
        log.info("[ratelimit] Redis mode | url=%s", redis_url.split("@")[-1])

    def _key(self, request: Request, endpoint: str) -> str:
        ip = _extract_ip(request)
        return f"rl:{endpoint}:{ip}"

    async def check(self, request: Request, limit: int, window: int = 60,
                    endpoint: str = "") -> None:
        key    = self._key(request, endpoint or request.url.path)
        now    = time.time()
        cutoff = now - window

        pipe = self._r.pipeline()
        pipe.zremrangebyscore(key, "-inf", cutoff)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window + 1)
        _, count, *_ = pipe.execute()

        if count >= limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error":       "rate_limit_exceeded",
                    "message":     "لقد تجاوزت الحد المسموح به من الطلبات. يرجى الانتظار قليلاً.",
                    "retry_after": window,
                },
                headers={"Retry-After": str(window)},
            )


# ── In-memory limiter (fallback) ────────────────────────────────────────────

class _MemoryLimiter:
    """Sliding-window per (IP, endpoint). Thread-safe. Single-process only."""

    def __init__(self) -> None:
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        log.info("[ratelimit] memory mode (single-process)")

    def _key(self, request: Request, endpoint: str) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        return f"{ip}:{endpoint}"

    async def check(self, request: Request, limit: int, window: int = 60,
                    endpoint: str = "") -> None:
        key    = self._key(request, endpoint or request.url.path)
        now    = time.monotonic()
        cutoff = now - window

        with self._lock:
            dq = self._windows[key]
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= limit:
                retry_after = int(window - (now - dq[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error":       "rate_limit_exceeded",
                        "message":     "لقد تجاوزت الحد المسموح به من الطلبات. يرجى الانتظار قليلاً.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            dq.append(now)


# ── Singleton: Redis → fakeredis → memory ──────────────────────────────────

def _build_limiter():
    if _REDIS_URL:
        try:
            return _RedisLimiter(_REDIS_URL)
        except Exception as e:
            log.warning("[ratelimit] Redis unavailable (%s) — trying fakeredis", e)
            try:
                import fakeredis
                server = fakeredis.FakeServer()
                fake_r = fakeredis.FakeRedis(server=server, decode_responses=True)
                fake_r.ping()
                limiter = _RedisLimiter.__new__(_RedisLimiter)
                limiter._r = fake_r
                log.info("[ratelimit] fakeredis mode (dev/single-process)")
                return limiter
            except Exception as fe:
                log.warning("[ratelimit] fakeredis unavailable (%s) — memory fallback", fe)
    return _MemoryLimiter()


_limiter = _build_limiter()


async def limit_analyze(request: Request) -> None:
    """5 analysis requests per minute per IP."""
    await _limiter.check(request, limit=5, window=60, endpoint="analyze")


async def limit_chat(request: Request) -> None:
    """30 chat requests per minute per IP."""
    await _limiter.check(request, limit=30, window=60, endpoint="chat")


async def limit_search(request: Request) -> None:
    """60 search requests per minute per IP."""
    await _limiter.check(request, limit=60, window=60, endpoint="search")
