from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
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
    gemini_model: str = "gemini-3.8-flash"
    addis_ai_api_key: str = Field(default="", validation_alias=AliasChoices("ADDIS_AI_API_KEY", "ADDIS_API_KEY", "addis_ai_api_key"))
    addis_ai_base_url: str = ""
    addis_tts_url: str = ""
    alibaba_dashscope_api_key: str = ""
    # Optional endpoint overrides retained for DashScope account-specific routing.
    alibaba_sensevoice_url: str = ""
    alibaba_cosyvoice_url: str = ""
    alibaba_ws_base: str = ""
    alibaba_workspace_id: str = ""
    alibaba_chinese_stt_model: str = "sensevoice-v1"
    alibaba_chinese_tts_model: str = "qwen-audio-3.0-tts-flash"
    alibaba_chinese_tts_sample_rate: int = 16000
    translation_provider: str = "gemini"
    ai_request_timeout_seconds: float = 20.0
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_url: str = ""
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
