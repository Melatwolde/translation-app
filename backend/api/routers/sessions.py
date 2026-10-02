from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from database import Database, get_database
from dependencies import get_current_user
from models.session import AudioProcessRequest, AudioProcessResponse, SessionContextUpdate, SessionCreate, SessionResponse
from models.user import UserProfile
from redis_client import RedisStore, get_redis
from services.session_service import SessionService
from services.translation_pipeline import TranslationPipeline

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def get_session_service(database: Database = Depends(get_database), redis: RedisStore = Depends(get_redis)) -> SessionService:
    return SessionService(database, redis, TranslationPipeline())


@router.post("", response_model=SessionResponse)
async def create_session(request: SessionCreate, user: UserProfile = Depends(get_current_user), service: SessionService = Depends(get_session_service)) -> SessionResponse:
    return await service.create(user.id, request)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID, user: UserProfile = Depends(get_current_user), service: SessionService = Depends(get_session_service)) -> SessionResponse:
    return await service.get_owned(user.id, session_id)


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(session_id: UUID, user: UserProfile = Depends(get_current_user), service: SessionService = Depends(get_session_service)) -> SessionResponse:
    return await service.end(user.id, session_id)


@router.post("/{session_id}/process-audio", response_model=AudioProcessResponse)
async def process_audio(session_id: UUID, request: AudioProcessRequest, user: UserProfile = Depends(get_current_user), service: SessionService = Depends(get_session_service)) -> AudioProcessResponse:
    return await service.process_audio(user.id, session_id, request.audio_base64, request.original_sample_rate)


@router.post("/{session_id}/context", response_model=list[str])
async def update_context(session_id: UUID, request: SessionContextUpdate, user: UserProfile = Depends(get_current_user), service: SessionService = Depends(get_session_service)) -> list[str]:
    return await service.set_context(user.id, session_id, request)
