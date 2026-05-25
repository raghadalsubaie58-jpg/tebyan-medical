"""OCR Agent — extracts raw text from PDF or image files."""
from __future__ import annotations
import fitz
from .base import AgentBase, AgentContext, _SoftDegradation


class OCRAgent(AgentBase):
    name = "ocr_agent"
    max_retries = 2

    def __init__(self, reader, vision_key: str = ""):
        self._reader     = reader
        self._vision_key = vision_key

    def _execute(self, ctx: AgentContext) -> None:
        if ctx.file_type == "pdf":
            ctx.raw_text = self._ocr_pdf(ctx.file_bytes)
        else:
            ctx.raw_text = self._ocr_image(ctx.file_bytes)

        if len(ctx.raw_text.strip()) < 50:
            raise _SoftDegradation(f"Very short OCR output: {len(ctx.raw_text)} chars")

        ctx.memory.remember("text_length", len(ctx.raw_text))

    def _ocr_pdf(self, data: bytes) -> str:
        from services.agent._ocr_helpers import preprocess_image
        doc      = fitz.open(stream=data, filetype="pdf")
        raw_text = "\n".join(p.get_text() for p in doc)
        if len(raw_text.strip()) >= 200:
            return raw_text
        parts = []
        for page in doc:
            pix  = page.get_pixmap(dpi=200)
            text = "\n".join(self._reader.readtext(preprocess_image(pix.tobytes("png")), detail=0))
            parts.append(text)
        return "\n".join(parts)

    def _ocr_image(self, data: bytes) -> str:
        from services.agent._ocr_helpers import preprocess_image, extract_text_google_vision
        if self._vision_key:
            try:
                return extract_text_google_vision(data, self._vision_key)
            except Exception as e:
                import logging
                logging.getLogger("tebyan.agents").warning("[ocr] Vision fallback: %s", e)
        return "\n".join(self._reader.readtext(preprocess_image(data), detail=0))

    def _on_failure(self, ctx: AgentContext, exc: Exception) -> None:
        ctx.raw_text = ""
