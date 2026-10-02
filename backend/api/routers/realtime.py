from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from database import get_database
from dependencies import decode_access_token, get_current_user
from models.session import LiveKitTokenResponse
from models.user import UserProfile
from redis_client import get_redis
from routers.sessions import get_session_service
from services.livekit_service import LiveKitService
from services.audio_utils import AudioFormatError, ensure_pcm16_16k_mono
from services.realtime_orchestrator import RealtimeSession
from services.session_service import SessionService
from services.translation_pipeline import TranslationPipeline

router = APIRouter(tags=["realtime"])


@router.post("/sessions/{session_id}/livekit-token", response_model=LiveKitTokenResponse)
async def livekit_token(session_id: UUID, user: UserProfile = Depends(get_current_user), service: SessionService = Depends(get_session_service)) -> LiveKitTokenResponse:
    await service.get_owned(user.id, session_id)
    livekit = LiveKitService()
    room_name = await livekit.create_room(str(session_id))
    return LiveKitTokenResponse(room_name=room_name, token=await livekit.generate_token(str(user.id), room_name))


@router.websocket("/ws/sessions/{session_id}")
async def realtime_websocket(websocket: WebSocket, session_id: UUID) -> None:
    token = websocket.query_params.get("token")
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        user_id = decode_access_token(token)
        database = await get_database()
        redis = await get_redis()
        service = await get_session_service(database, redis)
        session = await service.get_owned(user_id, session_id)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    orchestrator = RealtimeSession(str(session_id), session.source_language, session.target_language, TranslationPipeline())
    await websocket.accept()
    try:
        while True:
            try:
                # AUDIO CONTRACT: 16 kHz mono signed little-endian PCM16 only.
                audio = ensure_pcm16_16k_mono(await websocket.receive_bytes())
            except AudioFormatError as error:
                await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason=str(error))
                return
            for frame in await orchestrator.ingest_audio(audio):
                if frame.kind == "json":
                    await websocket.send_json(frame.payload)
                else:
                    await websocket.send_bytes(frame.payload if isinstance(frame.payload, bytes) else b"")
    except WebSocketDisconnect:
        return
