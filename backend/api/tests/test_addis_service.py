from __future__ import annotations

import asyncio

import httpx
import pytest

from config import Settings
from services.addis_service import AddisAIService


async def test_addis_stt_and_tts_use_configured_http_api() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/stt"
        assert request.headers["x-api-key"] == "test"
        return httpx.Response(200, json={"status": "success", "data": {"transcription": "salam"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = AddisAIService(Settings(addis_ai_api_key="test", addis_ai_base_url="https://addis.test"), client)
        assert await service.transcribe(b"\x00\x00", "am") == "salam"


async def test_addis_missing_key_raises_clear_error() -> None:
    with pytest.raises(RuntimeError, match="ADDIS_AI_API_KEY"):
        await AddisAIService(Settings(ADDIS_AI_API_KEY="", addis_ai_base_url="https://addis.test")).transcribe(b"pcm", "am")


async def test_addis_timeout_is_propagated() -> None:
    class SlowAddis(AddisAIService):
        async def _post_stt(self, audio: bytes, language: str) -> dict[str, object]:
            await asyncio.sleep(0.05)
            return {"status": "success", "data": {"transcription": "late"}}

    service = SlowAddis(Settings(addis_ai_api_key="key", addis_ai_base_url="https://addis.test", ai_request_timeout_seconds=0.001))
    with pytest.raises(TimeoutError):
        await service.transcribe(b"pcm", "am")
