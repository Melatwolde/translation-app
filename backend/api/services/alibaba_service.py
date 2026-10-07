"""Small DashScope WebSocket adapter for the Chinese speech leg.

DashScope accounts can expose different speech protocol revisions. Confirm the
enabled model and event schema in the DashScope console before deployment.
"""
from __future__ import annotations

import asyncio
import base64
import json
from uuid import uuid4
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlencode

from config import Settings, get_settings
from services.audio_utils import ensure_pcm16_16k_mono


def split_frame(frame: str | bytes) -> tuple[str, dict[str, Any] | bytes]:
    """Classify a WebSocket frame without trying to JSON-decode audio."""
    if isinstance(frame, bytes):
        return "audio", frame
    try:
        
        value = json.loads(frame)
    except json.JSONDecodeError:
        return "text", {"text": frame}
    if not isinstance(value, dict):
        raise RuntimeError("DashScope control frame must be a JSON object")
    return "json", value


def _event_name(message: dict[str, Any]) -> str:
    header = message.get("header")
    return str(message.get("event") or message.get("type") or (header.get("event") if isinstance(header, dict) else "") or (header.get("name") if isinstance(header, dict) else "") or "").lower()


class AlibabaService:
    """Timeout-bounded WebSocket calls using Bearer DashScope authentication."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _base_url(self) -> str:
        if self.settings.alibaba_ws_base:
            return self.settings.alibaba_ws_base.rstrip("/")
        if self.settings.alibaba_workspace_id:
            return f"wss://{self.settings.alibaba_workspace_id}.cn-beijing.maas.aliyuncs.com/api-ws/v1"
        return "wss://dashscope.aliyuncs.com/api-ws/v1"

    def _url(self, family: str, model: str) -> str:
        override = (
            self.settings.alibaba_sensevoice_url if model == self.settings.alibaba_chinese_stt_model
            else self.settings.alibaba_cosyvoice_url if model == self.settings.alibaba_chinese_tts_model else ""
        )
        if override:
            if not override.startswith("wss://") or override.startswith("wss://://"):
                raise ValueError("Alibaba WebSocket endpoint overrides must be valid wss:// URLs")
            return override
        suffix = "realtime" if family == "realtime" else "inference"
        url = f"{self._base_url()}/{suffix}"
        return f"{url}?{urlencode({'model': model})}" if family == "realtime" else url

    def _headers(self) -> dict[str, str]:
        if not self.settings.alibaba_dashscope_api_key:
            raise RuntimeError("ALIBABA_DASHSCOPE_API_KEY is required for Alibaba speech services")
        return {"Authorization": f"Bearer {self.settings.alibaba_dashscope_api_key}"}

    async def _connect(self, url: str):
        try:
            from websockets.asyncio.client import connect
        except ImportError as error:  # pragma: no cover
            raise RuntimeError("The 'websockets' package is required for Alibaba speech services") from error
        return connect(url, additional_headers=self._headers(), open_timeout=self.settings.ai_request_timeout_seconds)

    async def _run_inference(self, *, model: str, task: str, text: str | None = None, audio: bytes | None = None) -> list[str | bytes]:
        """Run the inference-family task lifecycle and collect terminal frames."""
        if audio is not None and len(audio) % 2:
            raise ValueError("Alibaba STT requires PCM16 audio with complete samples")
        timeout = self.settings.ai_request_timeout_seconds
        results: list[str | bytes] = []
        task_id = str(uuid4())
        async with await self._connect(self._url("inference", model)) as websocket:
            run_payload: dict[str, Any] = {
                "model": model,
                "parameters": {"format": "pcm", "sample_rate": 16000, "language_hints": ["zh"]},
            }
            if task == "tts":
                # The duplex TTS protocol requires an input object on every
                # lifecycle message, including run-task and finish-task.
                run_payload = {
                    "task_group": "audio",
                    "task": "tts",
                    "function": "SpeechSynthesizer",
                    "model": model,
                    "parameters": {
                        "text_type": "PlainText",
                        "voice": "longanhuan_v3.6",
                        "format": "pcm",
                        "sample_rate": 16000,
                    },
                    "input": {},
                }
            await asyncio.wait_for(websocket.send(json.dumps({
                "header": {"action": "run-task", "task_id": task_id, "streaming": "duplex"},
                "payload": run_payload,
            })), timeout)
            await self._wait_for_started(websocket)
            if audio is not None:
                await asyncio.wait_for(websocket.send(audio), timeout)
            elif text is not None:
                await asyncio.wait_for(websocket.send(json.dumps({
                    "header": {"action": "continue-task", "task_id": task_id, "streaming": "duplex"},
                    "payload": {"input": {"text": text}},
                })), timeout)
            await asyncio.wait_for(websocket.send(json.dumps({
                "header": {"action": "finish-task", "task_id": task_id, "streaming": "duplex"},
                "payload": {"input": {}} if task == "tts" else {},
            })), timeout)
            async for frame in self._frames_until_terminal(websocket):
                results.append(frame)
        return results

    async def _wait_for_started(self, websocket: Any) -> None:
        while True:
            kind, payload = split_frame(await asyncio.wait_for(websocket.recv(), self.settings.ai_request_timeout_seconds))
            if kind != "json":
                continue
            event = _event_name(payload)
            if event in {"task-started", "task_started", "started"}:
                return
            if event in {"error", "task-failed", "failed"}:
                raise RuntimeError(f"DashScope task failed: {payload}")

    async def _frames_until_terminal(self, websocket: Any) -> AsyncIterator[str | bytes]:
        while True:
            kind, payload = split_frame(await asyncio.wait_for(websocket.recv(), self.settings.ai_request_timeout_seconds))
            if kind == "audio":
                yield payload
                continue
            if kind == "text":
                continue
            event = _event_name(payload)
            if event in {"error", "task-failed", "failed"}:
                raise RuntimeError(f"DashScope task failed: {payload}")
            payload_body = payload.get("payload")
            output = (payload_body.get("output") if isinstance(payload_body, dict) else None) or payload.get("output")
            source = output if isinstance(output, dict) else payload
            for key in ("text", "transcript"):
                if isinstance(source.get(key), str):
                    yield source[key]
            encoded = source.get("audio_pcm16_base64")
            if isinstance(encoded, str):
                yield base64.b64decode(encoded)
            if event in {"task-finished", "task_finished", "finished", "completed"}:
                return

    async def transcribe_chinese_stream(self, audio: bytes) -> str:
        parts = await self._run_inference(model=self.settings.alibaba_chinese_stt_model, task="asr", audio=audio)
        transcript = "".join(part for part in parts if isinstance(part, str)).strip()
        if not transcript:
            raise RuntimeError("DashScope ASR response did not contain a transcript")
        return transcript

    async def transcribe_chinese(self, audio: bytes) -> str:
        return await self.transcribe_chinese_stream(audio)

    async def synthesize_chinese_stream(self, text: str) -> bytes:
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")
        parts = await self._run_inference(model=self.settings.alibaba_chinese_tts_model, task="tts", text=text)
        audio = b"".join(part for part in parts if isinstance(part, bytes))
        if not audio:
            raise RuntimeError("DashScope TTS response did not contain PCM16 audio")
        # The pipeline contract is always 16 kHz; configure the source rate if
        # a selected DashScope voice only emits (for example) 24 kHz PCM.
        return ensure_pcm16_16k_mono(audio, self.settings.alibaba_chinese_tts_sample_rate)

    async def synthesize_chinese(self, text: str) -> bytes:
        return await self.synthesize_chinese_stream(text)
