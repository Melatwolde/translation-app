from __future__ import annotations

import importlib
import inspect
from typing import Any

from config import Settings, get_settings


async def _call(method: Any, **kwargs: Any) -> Any:
    result = method(**kwargs)
    return await result if inspect.isawaitable(result) else result


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("text", value.get("transcript", "")))
    return str(getattr(value, "text", getattr(value, "transcript", "")))


def _audio(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, dict):
        return bytes(value.get("audio", b""))
    return bytes(getattr(value, "audio", b""))


class AddisAIService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def transcribe(self, audio: bytes, language: str) -> str:
        if not self.settings.addis_ai_api_key:
            return f"transcript:{language}"
        try:
            sdk = importlib.import_module("addisai")
            method = getattr(sdk, "transcribe_audio")
            return _text(await _call(method, audio=audio, language=language, api_key=self.settings.addis_ai_api_key))
        except (ImportError, AttributeError):
            return f"transcript:{language}"

    async def synthesize(self, text: str, language: str) -> bytes:
        if not self.settings.addis_ai_api_key:
            return f"{language}:{text}".encode("utf-8")
        try:
            sdk = importlib.import_module("addisai")
            method = getattr(sdk, "synthesize_speech")
            return _audio(await _call(method, text=text, language=language, api_key=self.settings.addis_ai_api_key))
        except (ImportError, AttributeError):
            return f"{language}:{text}".encode("utf-8")
