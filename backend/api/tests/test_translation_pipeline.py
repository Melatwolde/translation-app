from __future__ import annotations

from services.translation_pipeline import TranslationPipeline


class StubAddis:
    async def transcribe(self, _: bytes, language: str) -> str:
        return f"addis-stt:{language}"

    async def synthesize(self, text: str, language: str) -> bytes:
        return f"addis-tts:{language}:{text}".encode()


class StubGemini:
    async def transcribe(self, _: bytes, language: str) -> str:
        return f"gemini-stt:{language}"

    async def translate(self, text: str, source: str, target: str) -> str:
        return f"translation:{source}:{target}:{text}"

    async def synthesize(self, text: str, language: str) -> bytes:
        return f"gemini-tts:{language}:{text}".encode()


async def test_pipeline_routes_addis_source_to_gemini_target() -> None:
    result = await TranslationPipeline(StubAddis(), StubGemini()).translate_audio(b"pcm", "am", "en")
    assert result.source_text == "addis-stt:am"
    assert result.audio.startswith(b"gemini-tts:en:")
    assert result.latency_ms >= 0


async def test_pipeline_routes_gemini_source_to_addis_target() -> None:
    result = await TranslationPipeline(StubAddis(), StubGemini()).translate_audio(b"pcm", "zh", "om")
    assert result.source_text == "gemini-stt:zh"
    assert result.audio.startswith(b"addis-tts:om:")
