from __future__ import annotations

import base64
import importlib
import inspect
from typing import Any

from config import Settings, get_settings


async def _await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def _response_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("text", ""))
    return str(getattr(value, "text", ""))


class GeminiService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _sdk(self) -> Any | None:
        if not self.settings.gemini_api_key:
            return None
        try:
            sdk = importlib.import_module("google.generativeai")
            sdk.configure(api_key=self.settings.gemini_api_key)
            return sdk
        except ImportError:
            return None

    async def transcribe(self, audio: bytes, language: str) -> str:
        sdk = self._sdk()
        if sdk is None:
            return f"transcript:{language}"
        model = sdk.GenerativeModel("gemini-1.5-flash")
        prompt = f"Transcribe this {language} PCM16 audio. Return only the transcript."
        content = [prompt, {"mime_type": "audio/pcm", "data": base64.b64encode(audio).decode("ascii")}]
        response = await _await(model.generate_content_async(content))
        return _response_text(response)

    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        sdk = self._sdk()
        if sdk is None:
            return f"[{source_language}->{target_language}] {text}"
        model = sdk.GenerativeModel("gemini-1.5-flash")
        prompt = f"Translate from {source_language} to {target_language}. Return only the translation: {text}"
        response = await _await(model.generate_content_async(prompt))
        return _response_text(response)

    async def synthesize(self, text: str, language: str) -> bytes:
        sdk = self._sdk()
        if sdk is None or not hasattr(sdk, "generate_audio_async"):
            return f"{language}:{text}".encode("utf-8")
        response = await _await(sdk.generate_audio_async(text=text, language=language))
        if isinstance(response, bytes):
            return response
        if isinstance(response, dict):
            return bytes(response.get("audio", b""))
        return bytes(getattr(response, "audio", b""))
