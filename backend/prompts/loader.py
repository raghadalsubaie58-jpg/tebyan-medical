"""
Prompt loader — loads and renders prompt templates from the prompts/ directory.
Usage:
    from prompts.loader import render, load
    prompt = render("templates/cbc_analysis_prompt", FINDINGS="...", RAG_CONTEXT="...")
"""
from __future__ import annotations
import pathlib
import re

_ROOT = pathlib.Path(__file__).parent

# In-memory cache: filename → raw text
_cache: dict[str, str] = {}


def load(name: str) -> str:
    """
    Load a prompt file by name (without extension).
    Supports subdirs: 'templates/cbc_analysis_prompt'
    Falls back to '' if file not found — never raises.
    """
    if name in _cache:
        return _cache[name]
    for ext in (".txt", ".md", ""):
        path = _ROOT / (name + ext)
        if path.exists():
            _cache[name] = path.read_text(encoding="utf-8")
            return _cache[name]
    _cache[name] = ""
    return ""


def render(name: str, **kwargs: str) -> str:
    """
    Load and fill {{PLACEHOLDER}} variables.
    Strips any unfilled placeholders after substitution.
    """
    tmpl = load(name)
    for key, val in kwargs.items():
        tmpl = tmpl.replace(f"{{{{{key}}}}}", str(val))
    # Remove any remaining {{UNFILLED}} markers
    tmpl = re.sub(r"\{\{[A-Z_]+\}\}", "", tmpl)
    return tmpl.strip()


def clear_cache() -> None:
    _cache.clear()


def list_available() -> list[str]:
    return [
        str(p.relative_to(_ROOT).with_suffix(""))
        for p in _ROOT.rglob("*.txt")
    ]
