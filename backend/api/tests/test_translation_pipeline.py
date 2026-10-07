from __future__ import annotations

import pytest

from config import Settings
from services.translation_pipeline import DuplexTranslationSession, TranslationPipeline
from services.translation_service import TranslationService


class StubAddis:
    async def transcribe(self, _: bytes, language: str) -> str:
        return f"addis-stt:{language}"

    async def synthesize(self, text: str, language: str) -> bytes:
        return f"addis-tts:{language}:{text}".encode()


class StubAlibaba:
    async def transcribe_chinese(self, _: bytes) -> str:
        return "alibaba-stt:zh"

    async def synthesize_chinese(self, text: str) -> bytes:
        return f"alibaba-tts:{text}".encode()


class StubTranslator:
    settings = Settings(translation_provider="gemini")

    async def translate(self, text: str, source: str, target: str, context_turns: list[str] | None = None) -> str:
        return f"translation:{source}:{target}:{text}"


async def test_pipeline_routes_addis_to_alibaba() -> None:
    result = await TranslationPipeline(StubAddis(), StubAlibaba(), StubTranslator()).translate_audio(b"\x00\x00", "am", "zh")
    assert result.source_text == "addis-stt:am"
    assert result.audio.startswith(b"alibaba-tts:")
    assert result.provider_path == "addis_stt->gemini_mt->alibaba_tts"


async def test_pipeline_routes_alibaba_to_addis() -> None:
    result = await TranslationPipeline(StubAddis(), StubAlibaba(), StubTranslator()).translate_audio(b"\x00\x00", "zh-CN", "om")
    assert result.source_text == "alibaba-stt:zh"
    assert result.audio.startswith(b"addis-tts:om:")


async def test_pipeline_rejects_unsupported_language_pair() -> None:
    with pytest.raises(ValueError, match="Unsupported language pair"):
        await TranslationPipeline(StubAddis(), StubAlibaba(), StubTranslator()).translate_audio(b"\x00\x00", "en", "am")


async def test_translation_service_missing_key_is_an_error() -> None:
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        await TranslationService(Settings(gemini_api_key="")).translate("hello", "am", "zh")


async def test_duplex_cross_talk_lock_discards_microphone_while_playing() -> None:
    session = DuplexTranslationSession(TranslationPipeline(StubAddis(), StubAlibaba(), StubTranslator()))
    await session.start()
    session.set_playback_active("zh", True)
    assert not await session.ingest_audio("zh", b"\x00\x00")
    assert session.audio_out["am"].empty()
    session.set_playback_active("zh", False)
    assert await session.ingest_audio("zh", b"\x00\x00")
    assert await session.audio_out["am"].get() == b"addis-tts:am:translation:zh:am:alibaba-stt:zh"
    await session.stop()
