"""Gemini-backed language services used by the translation pipeline."""
from __future__ import annotations

import asyncio
import wave
from io import BytesIO

from config import Settings, get_settings
from services.translation_service import TranslationService


class GeminiService(TranslationService):
    """Backward-compatible alias for Gemini text translation."""


class GeminiAudioService:
    """Gemini multimodal transcription for normalized PCM16 audio."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def transcribe_chinese(self, audio: bytes) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Chinese audio transcription")
        if len(audio) % 2:
            raise ValueError("Gemini STT requires complete PCM16 samples")
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:  # pragma: no cover
            raise RuntimeError("The 'google-genai' package is required for Gemini speech services") from error

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16_000)
            wav.writeframes(audio)
        client = genai.Client(api_key=self.settings.gemini_api_key)
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=[
                        "Transcribe the speech in this audio into Chinese. Return only the transcript.",
                        types.Part.from_bytes(data=buffer.getvalue(), mime_type="audio/wav"),
                    ],
                ),
                timeout=self.settings.ai_request_timeout_seconds,
            )
        finally:
            await client.aio.aclose()
        transcript = getattr(response, "text", None)
        if not isinstance(transcript, str) or not transcript.strip():
            raise RuntimeError("Gemini returned an empty Chinese transcript")
        return transcript.strip()
