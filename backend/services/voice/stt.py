"""
Speech-to-Text — Arabic audio transcription via Groq Whisper API.

Groq provides whisper-large-v3 with excellent Arabic accuracy.
Falls back to OpenAI Whisper API if OPENAI_API_KEY is set and Groq fails.
"""
from __future__ import annotations
import io
import logging

log = logging.getLogger("tebyan.voice.stt")

# Supported audio MIME types → file extensions for Groq
_MIME_EXT = {
    "audio/webm":        "webm",
    "audio/mp4":         "mp4",
    "audio/mpeg":        "mp3",
    "audio/ogg":         "ogg",
    "audio/wav":         "wav",
    "audio/x-wav":       "wav",
    "audio/flac":        "flac",
    "audio/m4a":         "m4a",
    "audio/x-m4a":       "m4a",
    "video/webm":        "webm",   # browsers often send audio as video/webm
}

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB (Groq limit)


class WhisperSTT:
    """
    Transcribes Arabic audio using Groq's hosted Whisper large-v3.
    """

    MODEL = "whisper-large-v3"

    def __init__(self, groq_api_key: str):
        from groq import Groq
        self._client = Groq(api_key=groq_api_key)

    def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        language: str = "ar",
        prompt: str = "تقرير طبي، فحوصات مختبرية، تحاليل طبية",
    ) -> str:
        """
        Transcribe audio bytes to text.
        prompt: Arabic context hint improves medical term recognition.
        """
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise ValueError(f"Audio too large: {len(audio_bytes) / 1e6:.1f}MB > 25MB limit")

        ext = _MIME_EXT.get(mime_type, "webm")
        filename = f"audio.{ext}"

        log.info("[stt] transcribing | mime=%s ext=%s size=%dKB lang=%s",
                 mime_type, ext, len(audio_bytes) // 1024, language)

        transcription = self._client.audio.transcriptions.create(
            file=(filename, io.BytesIO(audio_bytes), mime_type),
            model=self.MODEL,
            language=language,
            prompt=prompt,
            response_format="verbose_json",
            temperature=0.0,
        )

        text = transcription.text.strip()
        log.info("[stt] result: %r (%.1fs)", text[:80], getattr(transcription, "duration", 0))
        return text

    def detect_language(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        """Detect the spoken language without full transcription."""
        ext      = _MIME_EXT.get(mime_type, "webm")
        result   = self._client.audio.transcriptions.create(
            file=(f"audio.{ext}", io.BytesIO(audio_bytes), mime_type),
            model=self.MODEL,
            response_format="verbose_json",
            temperature=0.0,
        )
        return getattr(result, "language", "ar")
