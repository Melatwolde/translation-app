from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from services.addis_service import AddisAIService
from services.audio_utils import ensure_pcm16_16k_mono
from services.gemini_service import GeminiService

ADDIS_LANGUAGES = frozenset({"am", "om"})


@dataclass(frozen=True)
class PipelineResult:
    source_text: str
    translated_text: str
    audio: bytes
    latency_ms: int
    created_at: datetime


class TranslationPipeline:
    def __init__(self, addis: AddisAIService | None = None, gemini: GeminiService | None = None) -> None:
        self.addis = addis or AddisAIService()
        self.gemini = gemini or GeminiService()

    async def translate_audio(self, audio: bytes, source_language: str, target_language: str) -> PipelineResult:
        started = perf_counter()
        # AUDIO CONTRACT: 16 kHz mono signed little-endian PCM16 only.
        audio = ensure_pcm16_16k_mono(audio)
        stt = self.addis if source_language in ADDIS_LANGUAGES else self.gemini
        tts = self.addis if target_language in ADDIS_LANGUAGES else self.gemini
        source_text = await stt.transcribe(audio, source_language)
        translated_text = await self.gemini.translate(source_text, source_language, target_language)
        output_audio = await tts.synthesize(translated_text, target_language)
        return PipelineResult(
            source_text=source_text, translated_text=translated_text, audio=output_audio,
            latency_ms=round((perf_counter() - started) * 1000), created_at=datetime.now(UTC),
        )
