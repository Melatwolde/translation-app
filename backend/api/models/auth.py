from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from models.user import UserProfile


class OtpSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str = Field(min_length=6, max_length=32)


class OtpSendResponse(BaseModel):
    expires_in_seconds: int


class OtpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str = Field(min_length=6, max_length=32)
    code: str = Field(min_length=4, max_length=8)


class OtpVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
