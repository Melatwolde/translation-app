from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

from config import Settings
from services.gemini_service import GeminiService


async def test_gemini_service_is_translation_only(monkeypatch: object) -> None:
    used_models: list[str] = []

    class Models:
        async def generate_content(self, *, model: str, contents: str) -> SimpleNamespace:
            used_models.append(model)
            assert "Translate from am to zh" in contents
            return SimpleNamespace(text="模拟翻译")

    class AsyncClient:
        models = Models()

        async def aclose(self) -> None:
            return None

    class Client:
        def __init__(self, *, api_key: str) -> None:
            assert api_key == "test"
            self.aio = AsyncClient()

    sdk = SimpleNamespace(Client=Client)
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=sdk))
    service = GeminiService(Settings(gemini_api_key="test"))
    assert await service.translate("hello", "am", "zh") == "模拟翻译"
    assert used_models == ["gemini-3.8-flash"]
    assert not hasattr(service, "transcribe")
    assert not hasattr(service, "synthesize")


async def test_gemini_translation_honours_timeout(monkeypatch: object) -> None:
    class Models:
        async def generate_content(self, **_: object) -> SimpleNamespace:
            await asyncio.sleep(0.05)
            return SimpleNamespace(text="late")

    class AsyncClient:
        models = Models()

        async def aclose(self) -> None:
            return None

    class Client:
        def __init__(self, **_: object) -> None:
            self.aio = AsyncClient()

    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=SimpleNamespace(Client=Client)))
    service = GeminiService(Settings(gemini_api_key="test", ai_request_timeout_seconds=0.001))
    with pytest.raises(TimeoutError):
        await service.translate("hello", "am", "zh")
