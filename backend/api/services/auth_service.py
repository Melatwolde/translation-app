from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

import jwt
from fastapi import HTTPException, status

from config import Settings, get_settings
from database import Database
from models.auth import OtpSendResponse, OtpVerifyResponse
from redis_client import RedisStore


def normalize_phone(phone: str) -> str:
    return "+" + "".join(character for character in phone if character.isdigit())


class AuthService:
    def __init__(self, database: Database, redis: RedisStore, settings: Settings | None = None) -> None:
        self.database = database
        self.redis = redis
        self.settings = settings or get_settings()

    async def send_otp(self, phone: str) -> OtpSendResponse:
        normalized = normalize_phone(phone)
        await self.redis.set(f"otp:{normalized}", self.settings.otp_debug_code, ex=self.settings.otp_ttl_seconds)
        return OtpSendResponse(expires_in_seconds=self.settings.otp_ttl_seconds)

    async def verify_otp(self, phone: str, code: str) -> OtpVerifyResponse:
        normalized = normalize_phone(phone)
        stored_code = await self.redis.get(f"otp:{normalized}")
        if stored_code is None or stored_code != code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")
        await self.redis.delete(f"otp:{normalized}")
        user_id: UUID = uuid5(NAMESPACE_URL, f"translation-api:{normalized}")
        user = await self.database.upsert_user(user_id, normalized)
        token = jwt.encode({"sub": str(user.id), "phone": user.phone}, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)
        return OtpVerifyResponse(access_token=token, user=user)
