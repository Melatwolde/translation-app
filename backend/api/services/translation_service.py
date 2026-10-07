from __future__ import annotations

import asyncio
from collections.abc import Sequence

from config import Settings, get_settings


class TranslationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context_turns: Sequence[str] | None = None,
    ) -> str:
        """Translate supported conversation pairs with Gemini; return text only."""
        source = _normalise_language(source_language)
        target = _normalise_language(target_language)
        supported_pairs = {
            ("am", "zh"), ("zh", "am"), ("om", "zh"),
            ("zh", "om"), ("am", "en"), ("en", "am"),
        }
        if (source, target) not in supported_pairs:
            raise ValueError("Gemini translation supports am/om <-> zh and temporary am <-> en only")
        if self.settings.translation_provider != "gemini":
            raise ValueError("TRANSLATION_PROVIDER must be 'gemini'")
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when TRANSLATION_PROVIDER=gemini")
        context = (context_turns or ())[-3:]
        prompt = (
            f"Translate from {source} to {target}. Return only the translated text; "
            "do not add explanations, labels, transliterations, or quotation marks."
        )
        if context:
            prompt += "\nRecent conversation context (reference only):\n" + "\n".join(context)
        prompt += f"\nText to translate:\n{text}"
        try:
            from google import genai
        except ImportError as error:
            raise RuntimeError("The 'google-genai' package is required for Gemini translation") from error
        client = genai.Client(api_key=self.settings.gemini_api_key)
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(model=self.settings.gemini_model, contents=prompt),
                timeout=self.settings.ai_request_timeout_seconds,
            )
        finally:
            await client.aio.aclose()
        translated = getattr(response, "text", None)
        if not isinstance(translated, str) or not translated.strip():
            raise RuntimeError("Gemini returned an empty translation")
        return translated.strip()


def _normalise_language(language: str) -> str:
    normalized = language.lower()
    return "zh" if normalized in {"zh", "zh-cn", "chinese"} else normalized
