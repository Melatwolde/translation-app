"""Backward-compatible import name for Gemini translation only.

Gemini must not be used for speech recognition or synthesis in this project.
New code should import :class:`TranslationService` directly.
"""
from services.translation_service import TranslationService


class GeminiService(TranslationService):
    """Deprecated alias retained for imports; it exposes translation only."""
