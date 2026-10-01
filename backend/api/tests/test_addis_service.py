from __future__ import annotations

from types import SimpleNamespace

from config import Settings
from services.addis_service import AddisAIService


async def test_addis_stt_and_tts_use_mocked_sdk(monkeypatch: object) -> None:
    async def transcribe_audio(**_: object) -> dict[str, str]:
        return {"text": "salam"}

    async def synthesize_speech(**_: object) -> dict[str, bytes]:
        return {"audio": b"voice"}

    monkeypatch.setitem(__import__("sys").modules, "addisai", SimpleNamespace(transcribe_audio=transcribe_audio, synthesize_speech=synthesize_speech))
    service = AddisAIService(Settings(addis_ai_api_key="test"))
    assert await service.transcribe(b"pcm", "am") == "salam"
    assert await service.synthesize("salam", "om") == b"voice"
