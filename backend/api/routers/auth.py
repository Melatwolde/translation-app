from __future__ import annotations

from fastapi import APIRouter, Depends

from database import Database, get_database
from models.auth import OtpSendRequest, OtpSendResponse, OtpVerifyRequest, OtpVerifyResponse
from redis_client import RedisStore, get_redis
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-otp", response_model=OtpSendResponse)
async def send_otp(request: OtpSendRequest, database: Database = Depends(get_database), redis: RedisStore = Depends(get_redis)) -> OtpSendResponse:
    return await AuthService(database, redis).send_otp(request.phone)


@router.post("/verify-otp", response_model=OtpVerifyResponse)
async def verify_otp(request: OtpVerifyRequest, database: Database = Depends(get_database), redis: RedisStore = Depends(get_redis)) -> OtpVerifyResponse:
    return await AuthService(database, redis).verify_otp(request.phone, request.code)
