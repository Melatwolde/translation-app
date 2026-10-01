from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone: str
    display_name: str | None = None
    language_preferences: list[str] = Field(default_factory=list)
    created_at: datetime


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    language_preferences: list[str] | None = None


class UserProfileResponse(BaseModel):
    user: UserProfile
