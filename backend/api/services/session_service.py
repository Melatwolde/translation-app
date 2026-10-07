from __future__ import annotations

import base64
import binascii
import json
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from config import get_settings
from database import Database
from models.session import AudioProcessResponse, SessionContextUpdate, SessionCreate, SessionResponse, TranslationSegment
from redis_client import RedisStore
from services.translation_pipeline import TranslationPipeline
from services.audio_utils import AudioFormatError, ensure_pcm16_16k_mono


class SessionService:
    def __init__(self, database: Database, redis: RedisStore, pipeline: TranslationPipeline) -> None:
        self.database = database
        self.redis = redis
        self.pipeline = pipeline

    async def create(self, user_id: UUID, request: SessionCreate) -> SessionResponse:
        return await self.database.create_session(user_id, request)

    async def get_owned(self, user_id: UUID, session_id: UUID) -> SessionResponse:
        session = await self.database.get_session(session_id)
        if session is None or session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return session

    async def end(self, user_id: UUID, session_id: UUID) -> SessionResponse:
        await self.get_owned(user_id, session_id)
        session = await self.database.end_session(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return session

    async def process_audio(self, user_id: UUID, session_id: UUID, encoded_audio: str, original_sample_rate: int | None = None) -> AudioProcessResponse:
        session = await self.get_owned(user_id, session_id)
        if session.status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session has ended")
        try:
            audio = base64.b64decode(encoded_audio, validate=True)
        except (ValueError, binascii.Error) as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="audio_base64 is invalid") from error
        try:
            audio = ensure_pcm16_16k_mono(audio, original_sample_rate)
        except AudioFormatError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        try:
            result = await self.pipeline.translate_audio(audio, session.source_language, session.target_language)
        except (RuntimeError, TimeoutError) as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        segment = TranslationSegment(
            id=uuid4(), source_text=result.source_text, translated_text=result.translated_text,
            source_language=session.source_language, target_language=session.target_language,
            latency_ms=result.latency_ms, created_at=result.created_at,
        )
        return AudioProcessResponse(segment=segment, audio_base64=base64.b64encode(result.audio).decode("ascii"))

    async def set_context(self, user_id: UUID, session_id: UUID, context: SessionContextUpdate) -> list[str]:
        await self.get_owned(user_id, session_id)
        await self.redis.set(f"session:{session_id}:context", json.dumps(context.turns[-6:]), ex=get_settings().otp_ttl_seconds)
        return context.turns[-6:]
