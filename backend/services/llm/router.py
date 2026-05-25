"""
LLM Model Router — unified interface over Groq and HuggingFace Inference API.

Supported providers:
  groq   — default (llama-3.3-70b / llama-3.1-8b)
  hf     — HuggingFace Inference API (Jais-13b, AceGPT, CAMeL models)

Usage:
  router = get_router()
  text   = router.generate(messages, model_hint="arabic")
  stream = router.stream(messages)

Model hints:
  "analysis"  → large model (llama-3.3-70b or Jais-13b if arabic_mode)
  "chat"      → fast model (llama-3.1-8b or Jais-7b if arabic_mode)
  "arabic"    → force Arabic-specialized model when available
"""
from __future__ import annotations

import os
import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Generator

log = logging.getLogger("tebyan.llm")


# ── Abstract base ──────────────────────────────────────────────────────────

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.3) -> str: ...

    @abstractmethod
    def stream(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.5) -> Generator[str, None, None]: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


# ── Groq provider ──────────────────────────────────────────────────────────

class GroqProvider(LLMProvider):
    _MODEL_ANALYSIS = "llama-3.3-70b-versatile"
    _MODEL_CHAT     = "llama-3.1-8b-instant"

    def __init__(self, api_key: str, model_hint: str = "analysis"):
        from groq import Groq
        self._client     = Groq(api_key=api_key)
        self._model_hint = model_hint

    @property
    def name(self) -> str:
        return "groq"

    def _model(self, hint: str = "") -> str:
        h = hint or self._model_hint
        return self._MODEL_CHAT if h == "chat" else self._MODEL_ANALYSIS

    def generate(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.3,
                 model_hint: str = "") -> str:
        resp = self._client.chat.completions.create(
            model=self._model(model_hint),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

    def stream(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.5,
               model_hint: str = "") -> Generator[str, None, None]:
        stream = self._client.chat.completions.create(
            model=self._model(model_hint or "chat"),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ── HuggingFace Inference API provider ────────────────────────────────────

class HuggingFaceProvider(LLMProvider):
    """
    Wraps HuggingFace Inference API for Arabic-specialized models.
    Supported models:
      - core42/jais-13b-chat         (Arabic-English bilingual)
      - core42/jais-adapted-7b-chat  (smaller/faster)
      - ALLaM-7B-Instruct-preview    (Arabic LLM from SDAIA — when available)
    """

    _DEFAULT_MODEL  = "core42/jais-13b-chat"
    _FAST_MODEL     = "core42/jais-adapted-7b-chat"
    _HF_INFERENCE   = "https://api-inference.huggingface.co/models"

    def __init__(self, api_key: str, model_hint: str = "analysis"):
        self._key        = api_key
        self._model_hint = model_hint

    @property
    def name(self) -> str:
        return "huggingface"

    def _model(self, hint: str = "") -> str:
        h = hint or self._model_hint
        return self._FAST_MODEL if h == "chat" else self._DEFAULT_MODEL

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    def _messages_to_text(self, messages: list[dict]) -> str:
        parts = []
        for m in messages:
            role    = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"<s>[INST] <<SYS>>\n{content}\n<</SYS>>\n\n")
            elif role == "user":
                parts.append(f"{content} [/INST]")
            else:
                parts.append(f"{content} </s><s>[INST] ")
        return "".join(parts)

    def generate(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.3,
                 model_hint: str = "") -> str:
        import requests
        model = self._model(model_hint)
        payload = {
            "inputs": self._messages_to_text(messages),
            "parameters": {
                "max_new_tokens": min(max_tokens, 2048),
                "temperature": max(temperature, 0.01),
                "do_sample": temperature > 0.01,
                "return_full_text": False,
            },
        }
        url = f"{self._HF_INFERENCE}/{model}"
        try:
            r = requests.post(url, headers=self._headers(), json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and data:
                return data[0].get("generated_text", "")
            return str(data)
        except Exception as e:
            log.error("[HF] generate failed for %s: %s", model, e)
            raise

    def stream(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.5,
               model_hint: str = "") -> Generator[str, None, None]:
        # HF Inference API doesn't support streaming for all models;
        # generate fully then yield the result as one chunk
        text = self.generate(messages, max_tokens=max_tokens, temperature=temperature, model_hint=model_hint)
        yield text


# ── Router ─────────────────────────────────────────────────────────────────

class LLMRouter:
    """
    Routes LLM calls to the appropriate provider.
    Falls back to Groq when the preferred provider fails.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider | None = None):
        self._primary  = primary
        self._fallback = fallback

    def generate(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.3,
                 model_hint: str = "") -> str:
        try:
            result = self._primary.generate(messages, max_tokens=max_tokens,
                                            temperature=temperature, model_hint=model_hint)
            log.debug("[router] generate via %s | tokens≤%d", self._primary.name, max_tokens)
            return result
        except Exception as e:
            if self._fallback:
                log.warning("[router] primary %s failed (%s) — fallback to %s",
                            self._primary.name, e, self._fallback.name)
                return self._fallback.generate(messages, max_tokens=max_tokens,
                                               temperature=temperature, model_hint=model_hint)
            raise

    def stream(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.5,
               model_hint: str = "") -> Generator[str, None, None]:
        try:
            yield from self._primary.stream(messages, max_tokens=max_tokens,
                                            temperature=temperature, model_hint=model_hint)
        except Exception as e:
            if self._fallback:
                log.warning("[router] stream primary failed (%s) — fallback", e)
                yield from self._fallback.stream(messages, max_tokens=max_tokens,
                                                 temperature=temperature, model_hint=model_hint)
            else:
                raise

    @property
    def provider_name(self) -> str:
        return self._primary.name


@lru_cache(maxsize=1)
def get_router() -> LLMRouter:
    """
    Build the LLMRouter singleton from environment config.

    Env vars:
      GROQ_API_KEY        — required
      HF_API_KEY          — optional; enables HuggingFace provider
      LLM_PROVIDER        — "groq" (default) | "hf" | "hf_with_groq_fallback"
      ARABIC_MODEL_MODE   — "1" to prefer Arabic-specialized models
    """
    groq_key    = os.getenv("GROQ_API_KEY", "")
    hf_key      = os.getenv("HF_API_KEY", "")
    provider    = os.getenv("LLM_PROVIDER", "groq").lower()
    arabic_mode = os.getenv("ARABIC_MODEL_MODE", "0") == "1"

    groq_hint = "arabic" if arabic_mode else "analysis"
    groq_p    = GroqProvider(groq_key, model_hint=groq_hint) if groq_key else None
    hf_p      = HuggingFaceProvider(hf_key, model_hint=groq_hint) if hf_key else None

    if provider == "hf" and hf_p:
        primary, fallback = hf_p, groq_p
    elif provider == "hf_with_groq_fallback" and hf_p and groq_p:
        primary, fallback = hf_p, groq_p
    else:
        primary  = groq_p or hf_p
        fallback = hf_p if (provider != "groq" and hf_p and primary is not hf_p) else None

    if not primary:
        raise RuntimeError("No LLM provider configured. Set GROQ_API_KEY or HF_API_KEY.")

    log.info("[router] primary=%s fallback=%s arabic_mode=%s",
             primary.name, fallback.name if fallback else "none", arabic_mode)

    return LLMRouter(primary=primary, fallback=fallback)
