from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Literal

from services.translation_pipeline import TranslationPipeline


@dataclass(frozen=True)
class RealtimeFrame:
    kind: Literal["json", "audio"]
    payload: dict[str, object] | bytes


@dataclass
class RealtimeSession:
    session_id: str
    source_language: str
    target_language: str
    pipeline: TranslationPipeline
    silence_energy: int = 450
    min_audio_bytes: int = 320
    _buffer: bytearray = field(default_factory=bytearray)

    @staticmethod
    def energy(pcm16: bytes) -> int:
        usable = pcm16[: len(pcm16) - (len(pcm16) % 2)]
        if not usable:
            return 0
        samples = struct.unpack(f"<{len(usable) // 2}h", usable)
        return sum(abs(sample) for sample in samples) // len(samples)

    async def ingest_audio(self, pcm16: bytes) -> list[RealtimeFrame]:
        if self.energy(pcm16) >= self.silence_energy:
            self._buffer.extend(pcm16)
            return []
        return await self.flush()

    async def flush(self) -> list[RealtimeFrame]:
        if len(self._buffer) < self.min_audio_bytes:
            self._buffer.clear()
            return []
        result = await self.pipeline.translate_audio(bytes(self._buffer), self.source_language, self.target_language)
        self._buffer.clear()
        return [
            RealtimeFrame(kind="json", payload={"event": "translation", "session_id": self.session_id, "source_text": result.source_text, "translated_text": result.translated_text, "latency_ms": result.latency_ms}),
            RealtimeFrame(kind="audio", payload=result.audio),
        ]
