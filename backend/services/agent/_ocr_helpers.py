"""
OCR helper functions for the agent pipeline.
Mirrors preprocess_image and extract_text_google_vision from main.py.
"""
from __future__ import annotations
import io
import base64

import numpy as np
import requests as http_requests
from PIL import Image


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Enhance image quality for EasyOCR."""
    from PIL import ImageFilter, ImageEnhance
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    w, h = img.size
    min_side, max_side = min(w, h), max(w, h)
    if min_side < 1200:
        scale = min(1200 / min_side, 4000 / max_side)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    gray = img.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(2.2)
    gray = ImageEnhance.Sharpness(gray).enhance(2.5)
    gray = gray.filter(ImageFilter.SHARPEN)
    return np.array(gray.convert("RGB"))


def _preprocess_for_vision(image_bytes: bytes) -> bytes:
    from PIL import ImageEnhance
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    max_side = max(w, h)
    if max_side < 1500:
        scale = 1500 / max_side
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    if max(img.size) > 4000:
        scale = 4000 / max(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, optimize=True)
    return buf.getvalue()


def extract_text_google_vision(image_bytes: bytes, api_key: str) -> str:
    processed = _preprocess_for_vision(image_bytes)
    b64 = base64.b64encode(processed).decode("utf-8")
    payload = {
        "requests": [{
            "image": {"content": b64},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}],
            "imageContext": {
                "languageHints": ["ar", "en"],
                "textDetectionParams": {"enableTextDetectionConfidenceScore": True},
            },
        }]
    }
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    r = http_requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    resp = r.json()["responses"][0]
    return resp.get("fullTextAnnotation", {}).get("text", "")
