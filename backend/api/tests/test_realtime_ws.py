from __future__ import annotations

import struct

from config import Settings
from services.realtime_orchestrator import RealtimeSession
from services.translation_pipeline import TranslationPipeline


class StubAddis:
    async def transcribe(self, _: bytes, language: str) -> str:
        return language

    async def synthesize(self, _: str, __: str) -> bytes:
        return b"audio"


class StubAlibaba:
    async def synthesize_chinese(self, _: str) -> bytes:
        return b"audio"

    async def transcribe_chinese(self, _: bytes) -> str:
        return "zh"


class StubTranslator:
    settings = Settings(translation_provider="gemini")

    async def translate(self, text: str, _: str, __: str) -> str:
        return text


async def test_realtime_session_emits_json_then_audio_after_silence() -> None:
    pipeline = TranslationPipeline(StubAddis(), StubAlibaba(), StubTranslator())
    orchestrator = RealtimeSession("session", "am", "zh", pipeline)
    speech = struct.pack("<160h", *([1000] * 160))
    assert await orchestrator.ingest_audio(speech) == []
    frames = await orchestrator.ingest_audio(b"\x00\x00" * 10)
    assert frames[0].kind == "json"
    assert frames[1].kind == "audio"
    assert frames[1].payload == b"audio"
