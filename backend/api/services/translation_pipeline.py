from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter

from services.addis_service import AddisAIService
from services.audio_utils import ensure_pcm16_16k_mono
from services.alibaba_service import AlibabaService
from services.translation_service import TranslationService

ADDIS_LANGUAGES = frozenset({"am", "om"})
CHINESE_LANGUAGES = frozenset({"zh", "zh-cn", "chinese"})


@dataclass(frozen=True)
class PipelineResult:
    source_text: str
    translated_text: str
    audio: bytes
    latency_ms: int
    provider_path: str
    created_at: datetime


class TranslationPipeline:
    def __init__(
        self,
        addis: AddisAIService | None = None,
        alibaba: AlibabaService | None = None,
        translator: TranslationService | None = None,
    ) -> None:
        self.addis = addis or AddisAIService()
        self.alibaba = alibaba or AlibabaService()
        self.translator = translator or TranslationService()

    async def translate_audio(self, audio: bytes, source_language: str, target_language: str) -> PipelineResult:
        started = perf_counter()
        audio = ensure_pcm16_16k_mono(audio)
        source = source_language.lower()
        target = target_language.lower()
        mt_provider = self.translator.settings.translation_provider
        if source in ADDIS_LANGUAGES and target in CHINESE_LANGUAGES:
            source_text = await self.addis.transcribe(audio, source)
            translated_text = await self.translator.translate(source_text, source, "zh")
            output_audio = await self.alibaba.synthesize_chinese(translated_text)
            path = f"addis_stt->{mt_provider}_mt->alibaba_tts"
        elif source in CHINESE_LANGUAGES and target in ADDIS_LANGUAGES:
            source_text = await self.alibaba.transcribe_chinese(audio)
            translated_text = await self.translator.translate(source_text, "zh", target)
            output_audio = await self.addis.synthesize(translated_text, target)
            path = f"alibaba_stt->{mt_provider}_mt->addis_tts"
        elif target == "en" and (source in ADDIS_LANGUAGES or source in CHINESE_LANGUAGES):
            if source in ADDIS_LANGUAGES:
                source_text = await self.addis.transcribe(audio, source)
                stt_path = "addis_stt"
            else:
                source_text = await self.alibaba.transcribe_chinese(audio)
                source = "zh"
                stt_path = "alibaba_stt"
            translated_text = await self.translator.translate(source_text, source, "en")
            output_audio = b""
            path = f"{stt_path}->{mt_provider}_mt->no_english_tts"
        else:
            raise ValueError("Unsupported language pair. Supported: am/om -> zh and zh -> am/om; temporary target 'en' is text-only.")
        return PipelineResult(
            source_text=source_text, translated_text=translated_text, audio=output_audio,
            latency_ms=round((perf_counter() - started) * 1000), provider_path=path, created_at=datetime.now(UTC),
        )


@dataclass
class DuplexTranslationSession:
    """Two independent speech directions with per-listener echo suppression.

    Input ``zh`` is delivered to the Amharic listener and vice versa. A caller
    must call ``set_playback_active`` while it writes a returned audio frame to
    the phone leg; any microphone audio from that same leg is then discarded.
    """

    pipeline: TranslationPipeline
    on_audio: Callable[[str, bytes], Awaitable[None]] | None = None
    context_size: int = 4
    audio_out: dict[str, asyncio.Queue[bytes]] = field(
        default_factory=lambda: {"zh": asyncio.Queue(), "am": asyncio.Queue()}
    )
    _input: dict[str, asyncio.Queue[bytes | None]] = field(
        default_factory=lambda: {"zh": asyncio.Queue(), "am": asyncio.Queue()}
    )
    _playback_active: dict[str, bool] = field(default_factory=lambda: {"zh": False, "am": False})
    _context: deque[str] = field(default_factory=lambda: deque(maxlen=4))
    _runner: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._runner is None:
            self._runner = asyncio.create_task(self._run(), name="duplex-translation")

    async def _run(self) -> None:
        await asyncio.gather(self._loop("zh", "am"), self._loop("am", "zh"))

    async def ingest_audio(self, track: str, pcm16: bytes) -> bool:
        if track not in self._input:
            raise ValueError("track must be 'zh' or 'am'")
        if self._playback_active[track]:
            return False
        await self._input[track].put(ensure_pcm16_16k_mono(pcm16))
        return True

    def set_playback_active(self, track: str, active: bool) -> None:
        if track not in self._playback_active:
            raise ValueError("track must be 'zh' or 'am'")
        self._playback_active[track] = active

    async def _loop(self, source: str, destination: str) -> None:
        while True:
            pcm16 = await self._input[source].get()
            if pcm16 is None:
                return
            # Recheck after dequeue: playback could have begun while queued.
            if self._playback_active[source]:
                continue
            result = await self._translate_chunk(pcm16, source, destination)
            self._context.append(f"{source}: {result.source_text}\n{destination}: {result.translated_text}")
            if result.audio:
                await self.audio_out[destination].put(result.audio)
                if self.on_audio:
                    await self.on_audio(destination, result.audio)

    async def _translate_chunk(self, pcm16: bytes, source: str, destination: str) -> PipelineResult:
        # Keep context out of the batch API but pass it to MT on the live path.
        if source == "zh":
            text = await self.pipeline.alibaba.transcribe_chinese(pcm16)
            translated = await self.pipeline.translator.translate(text, "zh", "am", context_turns=list(self._context)[-3:])
            audio = await self.pipeline.addis.synthesize(translated, "am")
            path = f"alibaba_stt->{self.pipeline.translator.settings.translation_provider}_mt->addis_tts"
        else:
            text = await self.pipeline.addis.transcribe(pcm16, "am")
            translated = await self.pipeline.translator.translate(text, "am", "zh", context_turns=list(self._context)[-3:])
            audio = await self.pipeline.alibaba.synthesize_chinese(translated)
            path = f"addis_stt->{self.pipeline.translator.settings.translation_provider}_mt->alibaba_tts"
        return PipelineResult(text, translated, audio, 0, path, datetime.now(UTC))

    async def stop(self) -> None:
        if self._runner is None:
            return
        for queue in self._input.values():
            await queue.put(None)
        await self._runner
        self._runner = None
