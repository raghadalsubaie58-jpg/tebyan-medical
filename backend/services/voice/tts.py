"""
Text-to-Speech — Arabic TTS with multiple provider support.

Provider priority:
  1. Google Cloud TTS (if GOOGLE_TTS_KEY is set) — best Arabic quality
  2. gTTS (free, Google Translate TTS) — no key required
  3. ElevenLabs (if ELEVENLABS_KEY is set) — premium quality

Output: MP3 bytes, ready to stream to browser.
"""
from __future__ import annotations
import io
import logging

log = logging.getLogger("tebyan.voice.tts")

MAX_TEXT_CHARS = 3000   # trim long responses before TTS


def _truncate(text: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    """Trim text to TTS-safe length, cutting at sentence boundary."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    for sep in (".", "!", "?", "\n", "،", "؟"):
        idx = cut.rfind(sep)
        if idx > max_chars * 0.7:
            return cut[:idx + 1]
    return cut


class GoogleTTS:
    """Google Cloud Text-to-Speech — WaveNet Arabic voices."""
    VOICE = "ar-XA-Wavenet-A"  # Arabic female WaveNet
    LANG  = "ar-XA"

    def __init__(self, api_key: str):
        self._key = api_key

    def synthesize(self, text: str) -> bytes:
        import requests, base64
        text = _truncate(text)
        payload = {
            "input":       {"text": text},
            "voice":       {"languageCode": self.LANG, "name": self.VOICE},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.9},
        }
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self._key}"
        r   = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return base64.b64decode(r.json()["audioContent"])


class GTTSProvider:
    """Free Google Translate TTS via gTTS library."""

    def synthesize(self, text: str) -> bytes:
        from gtts import gTTS
        text = _truncate(text)
        buf  = io.BytesIO()
        tts  = gTTS(text=text, lang="ar", slow=False)
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()


class ElevenLabsTTS:
    """ElevenLabs TTS — premium multilingual quality."""
    MODEL   = "eleven_multilingual_v2"

    def __init__(self, api_key: str, voice_id: str = "pNInz6obpgDQGcFmaJgB"):
        self._key      = api_key
        self._voice_id = voice_id

    def synthesize(self, text: str) -> bytes:
        import requests
        text    = _truncate(text)
        url     = f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}"
        headers = {"xi-api-key": self._key, "Content-Type": "application/json"}
        payload = {
            "text":          text,
            "model_id":      self.MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.content


def get_tts_provider(google_tts_key: str = "", elevenlabs_key: str = ""):
    """Return the best available TTS provider."""
    if google_tts_key:
        log.info("[tts] using Google Cloud TTS")
        return GoogleTTS(google_tts_key)
    if elevenlabs_key:
        log.info("[tts] using ElevenLabs TTS")
        return ElevenLabsTTS(elevenlabs_key)
    try:
        import gtts  # noqa: F401
        log.info("[tts] using gTTS (free)")
        return GTTSProvider()
    except ImportError:
        raise RuntimeError(
            "No TTS provider available. Install gTTS (`pip install gtts`) or set "
            "GOOGLE_TTS_KEY / ELEVENLABS_KEY environment variables."
        )
