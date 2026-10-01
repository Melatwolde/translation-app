from __future__ import annotations

import struct

from services.realtime_orchestrator import RealtimeSession
from services.translation_pipeline import TranslationPipeline


class StubAddis:
    async def transcribe(self, _: bytes, language: str) -> str:
        return language

    async def synthesize(self, _: str, __: str) -> bytes:
        return b"audio"


class StubGemini:
    async def transcribe(self, _: bytes, language: str) -> str:
        return language

    async def translate(self, text: str, _: str, __: str) -> str:
        return text

    async def synthesize(self, _: str, __: str) -> bytes:
        return b"audio"


async def test_realtime_session_emits_json_then_audio_after_silence() -> None:
    orchestrator = RealtimeSession("session", "en", "am", TranslationPipeline(StubAddis(), StubGemini()))
    speech = struct.pack("<160h", *([1000] * 160))
    assert await orchestrator.ingest_audio(speech) == []
    frames = await orchestrator.ingest_audio(b"\x00\x00" * 10)
    assert frames[0].kind == "json"
    assert frames[0].payload["event"] == "translation"
    assert frames[1].kind == "audio"
    assert frames[1].payload == b"audio"
