"""
Request sanitization and file validation for medical file uploads.

Validates:
  - File size (max 20 MB)
  - MIME type whitelist (PDF, JPEG, PNG, WEBP, TIFF)
  - Magic bytes (header sniffing — prevents MIME spoofing)
  - Filename safety (path traversal, null bytes, dangerous extensions)
  - Text input: strips HTML tags, limits length, removes null bytes
"""
from __future__ import annotations

import re
from typing import Final

from fastapi import HTTPException, UploadFile

# ── Limits ───────────────────────────────────────────────────────────────────

MAX_FILE_BYTES: Final[int] = 20 * 1024 * 1024   # 20 MB
MAX_TEXT_LEN: Final[int]   = 8_000              # characters per text field

# ── Allowed MIME types (whitelist) ───────────────────────────────────────────

_ALLOWED_MIME: Final[frozenset[str]] = frozenset([
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/tiff",
])

# ── Magic bytes (first bytes of file → expected MIME group) ─────────────────

_MAGIC: Final[list[tuple[bytes, str]]] = [
    (b"%PDF",       "pdf"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG",    "png"),
    (b"RIFF",       "webp"),   # RIFF....WEBP
    (b"II*\x00",    "tiff"),   # little-endian TIFF
    (b"MM\x00*",    "tiff"),   # big-endian TIFF
]

_MIME_TO_MAGIC_GROUP: Final[dict[str, str]] = {
    "application/pdf": "pdf",
    "image/jpeg":      "jpeg",
    "image/jpg":       "jpeg",
    "image/png":       "png",
    "image/webp":      "webp",
    "image/tiff":      "tiff",
}

# ── Dangerous file extensions (block even if MIME seems OK) ──────────────────

_BLOCKED_EXT: Final[frozenset[str]] = frozenset([
    ".exe", ".sh", ".bat", ".cmd", ".ps1", ".js", ".php", ".py",
    ".rb", ".pl", ".dll", ".so", ".elf", ".msi", ".vbs", ".hta",
    ".jar", ".class", ".com", ".scr", ".pif",
])

# ── Text sanitization ────────────────────────────────────────────────────────

_HTML_TAG_RE  = re.compile(r"<[^>]{0,200}>")
_SCRIPT_RE    = re.compile(r"(?i)(javascript:|data:text/html|<script)", re.IGNORECASE)
_NULL_BYTE_RE = re.compile(r"\x00")
_SQL_INJECT   = re.compile(
    r"(?i)\b(union\s+select|drop\s+table|insert\s+into|delete\s+from"
    r"|exec\s*\(|xp_cmdshell|;--)\b"
)


def sanitize_text(text: str, max_len: int = MAX_TEXT_LEN) -> str:
    """
    Strip HTML, null bytes, and obvious injection patterns from user text.
    Truncates to max_len characters.
    """
    if not isinstance(text, str):
        return ""
    text = _NULL_BYTE_RE.sub("", text)
    text = _HTML_TAG_RE.sub("", text)
    if _SCRIPT_RE.search(text):
        raise HTTPException(status_code=400, detail="محتوى غير مسموح به في النص المرسل")
    if _SQL_INJECT.search(text):
        raise HTTPException(status_code=400, detail="محتوى غير مسموح به في النص المرسل")
    return text[:max_len].strip()


def _sniff_magic(data: bytes) -> str | None:
    """Return magic group name or None if unrecognised."""
    for magic, group in _MAGIC:
        if data[:len(magic)] == magic:
            # Special: WebP has 'WEBP' at offset 8
            if group == "webp" and data[8:12] != b"WEBP":
                continue
            return group
    return None


def _safe_filename(filename: str) -> str:
    """Sanitize filename: strip path components and dangerous characters."""
    # Strip directory traversal
    name = re.sub(r"[/\\]", "_", filename)
    # Remove null bytes and control chars
    name = re.sub(r"[\x00-\x1f]", "", name)
    # Keep only safe chars
    name = re.sub(r"[^\w.\-]", "_", name)
    return name[:128] or "upload"


def validate_upload(file: UploadFile, data: bytes) -> None:
    """
    Validate an uploaded file.  Raises HTTPException on any violation.

    Args:
        file: The UploadFile from FastAPI (provides filename + content_type).
        data: Raw bytes already read from the file.

    Raises:
        HTTPException 400 for bad requests, 413 for file too large, 415 for unsupported type.
    """
    # ── Size ─────────────────────────────────────────────────────────────────
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="الملف فارغ")
    if len(data) > MAX_FILE_BYTES:
        mb = MAX_FILE_BYTES // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"حجم الملف يتجاوز الحد المسموح ({mb} MB)")

    # ── Filename safety ───────────────────────────────────────────────────────
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="اسم الملف مطلوب")

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in _BLOCKED_EXT:
        raise HTTPException(status_code=415, detail=f"نوع الملف '{ext}' غير مسموح")

    # ── MIME whitelist ────────────────────────────────────────────────────────
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"نوع الملف '{content_type}' غير مدعوم. الأنواع المقبولة: PDF, JPEG, PNG, WEBP, TIFF",
        )

    # ── Magic bytes validation (anti-MIME-spoofing) ───────────────────────────
    detected = _sniff_magic(data)
    expected_group = _MIME_TO_MAGIC_GROUP.get(content_type)
    if detected is None:
        raise HTTPException(status_code=415, detail="تعذّر التحقق من نوع الملف — بيانات غير صالحة")
    if expected_group and detected != expected_group:
        raise HTTPException(
            status_code=415,
            detail=f"محتوى الملف لا يطابق نوعه المُعلَن ({content_type})",
        )
