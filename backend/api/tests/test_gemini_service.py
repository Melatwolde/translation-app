from __future__ import annotations

import sys
from types import SimpleNamespace

from config import Settings
from services.gemini_service import GeminiService


async def test_gemini_operations_use_mocked_sdk(monkeypatch: object) -> None:
    class Model:
        def __init__(self, _: str) -> None:
            pass

        async def generate_content_async(self, _: object) -> SimpleNamespace:
            return SimpleNamespace(text="mocked output")

    async def generate_audio_async(**_: object) -> dict[str, bytes]:
        return {"audio": b"audio"}

    sdk = SimpleNamespace(configure=lambda **_: None, GenerativeModel=Model, generate_audio_async=generate_audio_async)
    monkeypatch.setitem(sys.modules, "google.generativeai", sdk)
    service = GeminiService(Settings(gemini_api_key="test"))
    assert await service.transcribe(b"pcm", "en") == "mocked output"
    assert await service.translate("hello", "en", "zh") == "mocked output"
    assert await service.synthesize("hello", "zh") == b"audio"
