from __future__ import annotations

import asyncio
import base64
import json
import wave
from io import BytesIO

import httpx

from config import Settings, get_settings


class AddisAIService:
    """Addis STT client using the verified v2 multipart API."""

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client

    def _headers(self) -> dict[str, str]:
        if not self.settings.addis_ai_api_key:
            raise RuntimeError("ADDIS_AI_API_KEY (or ADDIS_API_KEY) is required for Addis AI")
        return {"x-api-key": self.settings.addis_ai_api_key}

    def _url(self, path: str) -> str:
        if not self.settings.addis_ai_base_url:
            raise RuntimeError("ADDIS_AI_BASE_URL is required; set it from the Addis AI dashboard")
        base = self.settings.addis_ai_base_url.rstrip("/")
        if base.endswith("/api") and path.startswith("/api/"):
            path = path[4:]
        return f"{base}{path}"

    async def _post_stt(self, audio: bytes, language: str) -> dict[str, object]:
        headers = self._headers()
        timeout = httpx.Timeout(self.settings.ai_request_timeout_seconds)
        files = {"audio": ("audio.wav", _pcm16_to_wav(audio), "audio/wav")}
        data = {"request_data": json.dumps({"language_code": language})}
        if self.client:
            response = await self.client.post(self._url("/api/v2/stt"), files=files, data=data, headers=headers, timeout=timeout)
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self._url("/api/v2/stt"), files=files, data=data, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Addis AI response must be a JSON object")
        return payload

    async def transcribe(self, audio: bytes, language: str) -> str:
        if language not in {"am", "om"}:
            raise ValueError("Addis AI supports only 'am' and 'om' in this pipeline")
        result = await asyncio.wait_for(self._post_stt(audio, language), self.settings.ai_request_timeout_seconds)
        data = result.get("data")
        text = data.get("transcription") if isinstance(data, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Addis AI response did not contain data.transcription")
        return text.strip()

    async def synthesize(self, text: str, language: str) -> bytes:
        if language not in {"am", "om"}:
            raise ValueError("Addis AI supports only 'am' and 'om' in this pipeline")
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")
        if not self.settings.addis_tts_url:
            raise RuntimeError("ADDIS_TTS_URL is required for Addis AI speech synthesis")
        headers = self._headers()
        timeout = self.settings.ai_request_timeout_seconds
        request = self.client.post if self.client else None
        if request:
            response = await asyncio.wait_for(
                request(self.settings.addis_tts_url, json={"text": text, "language_code": language}, headers=headers, timeout=timeout),
                timeout=timeout,
            )
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await asyncio.wait_for(
                    client.post(self.settings.addis_tts_url, json={"text": text, "language_code": language}, headers=headers),
                    timeout=timeout,
                )
        response.raise_for_status()
        if "application/json" in response.headers.get("content-type", ""):
            payload = response.json()
            data = payload.get("data", payload) if isinstance(payload, dict) else {}
            encoded_audio = data.get("audio_base64") or data.get("audio") if isinstance(data, dict) else None
            if not isinstance(encoded_audio, str):
                raise RuntimeError("Addis AI response did not contain base64 audio")
            try:
                audio = base64.b64decode(encoded_audio, validate=True)
            except ValueError as error:
                raise RuntimeError("Addis AI returned invalid base64 audio") from error
        else:
            audio = response.content
        if not audio:
            raise RuntimeError("Addis AI returned empty synthesized audio")
        return audio


def _pcm16_to_wav(pcm16: bytes) -> bytes:
    """Envelope the pipeline's raw PCM16 contract for Addis's file upload API."""
    if len(pcm16) % 2:
        raise ValueError("Addis STT requires complete PCM16 samples")
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(pcm16)
    return buffer.getvalue()
