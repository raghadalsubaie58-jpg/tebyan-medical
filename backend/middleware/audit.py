"""
Structured audit logging middleware for PDPL/NDMO compliance.

Every request is logged with: timestamp, method, path, client IP,
session_id (from header), status code, latency, and error summary.
Logs are written to a rotating file + stdout (structured JSON).
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ── Audit logger (separate from app logger) ─────────────────────────────────

_LOG_DIR = Path(os.getenv("AUDIT_LOG_DIR", "logs/audit"))
_LOG_FILE = _LOG_DIR / "audit.jsonl"
_MAX_BYTES = 50 * 1024 * 1024   # 50 MB per file
_BACKUP_COUNT = 10               # keep 10 rotated files (~500 MB total)

# Paths that are not audited (health checks, static assets)
_SKIP_PATHS = frozenset(["/health", "/docs", "/openapi.json", "/favicon.ico"])

# Endpoints that handle medical data — flag them for compliance
_SENSITIVE_PATHS = frozenset([
    "/api/analyze", "/api/analyses/save", "/api/chat",
    "/api/voice/transcribe", "/api/voice/chat", "/api/risk",
])


def _build_audit_logger() -> logging.Logger:
    logger = logging.getLogger("audit")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(fh)
    except Exception as e:
        print(f"[AUDIT] Cannot open log file {_LOG_FILE}: {e} — writing to stderr only")

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(sh)

    return logger


_audit_logger = _build_audit_logger()


def get_audit_logger() -> logging.Logger:
    return _audit_logger


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _redact_sensitive_headers(headers: dict) -> dict:
    """Remove auth tokens and API keys from logged headers."""
    sensitive = {"authorization", "x-api-key", "cookie", "set-cookie"}
    return {k: "[REDACTED]" if k.lower() in sensitive else v for k, v in headers.items()}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that writes one structured JSON audit record per request.

    Fields logged:
      req_id, timestamp_utc, method, path, query, client_ip,
      session_id, status, latency_ms, sensitive, error (if any)
    """

    def __init__(self, app: ASGIApp, environment: str = "production") -> None:
        super().__init__(app)
        self._env = environment

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        req_id = str(uuid.uuid4())[:8]
        t_start = time.perf_counter()

        # Attach req_id so endpoints can reference it in error messages
        request.state.req_id = req_id

        error_detail: str | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            error_detail = type(exc).__name__ + ": " + str(exc)[:200]
            raise
        finally:
            latency_ms = round((time.perf_counter() - t_start) * 1000, 1)
            path = request.url.path
            record: dict = {
                "req_id":        req_id,
                "ts":            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "method":        request.method,
                "path":          path,
                "query":         str(request.url.query)[:200] or None,
                "ip":            _get_client_ip(request),
                "session_id":    request.headers.get("X-Session-Id", "anon")[:64],
                "status":        status_code,
                "latency_ms":    latency_ms,
                "sensitive":     path in _SENSITIVE_PATHS,
                "env":           self._env,
            }
            if error_detail:
                record["error"] = error_detail
            _audit_logger.info(json.dumps(record, ensure_ascii=False))

        response.headers["X-Request-Id"] = req_id
        return response
