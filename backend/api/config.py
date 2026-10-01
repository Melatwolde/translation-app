from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-secret-change-me-please"
    jwt_algorithm: str = "HS256"
    otp_ttl_seconds: int = 300
    otp_debug_code: str = "123456"
    gemini_api_key: str = ""
    addis_ai_api_key: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_url: str = ""
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
