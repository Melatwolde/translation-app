from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LanguageCode = Literal["am", "om", "zh", "en"]
SessionStatus = Literal["active", "ended"]


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_language: LanguageCode
    target_language: LanguageCode


class SessionContextUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turns: list[str] = Field(max_length=6)


class AudioProcessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audio_base64: str = Field(min_length=1)
    original_sample_rate: int | None = Field(default=None, gt=0)


class TranslationSegment(BaseModel):
    id: UUID
    source_text: str
    translated_text: str
    source_language: LanguageCode
    target_language: LanguageCode
    latency_ms: int
    created_at: datetime


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    source_language: LanguageCode
    target_language: LanguageCode
    status: SessionStatus
    created_at: datetime
    ended_at: datetime | None = None


class AudioProcessResponse(BaseModel):
    segment: TranslationSegment
    audio_base64: str


class LiveKitTokenResponse(BaseModel):
    room_name: str
    token: str
