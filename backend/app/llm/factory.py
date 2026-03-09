"""Factory helpers for creating configured LLM providers."""

from __future__ import annotations

from app.config import get_settings
from app.llm.base import LLMProvider


def make_llm(provider_override: str | None = None) -> LLMProvider:
    """Create the primary LLM provider from settings or explicit override."""
    settings = get_settings()
    provider = (provider_override or settings.llm_provider).lower()

    if provider == "auto":
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            provider = "bedrock"
        elif settings.gemini_api_key:
            provider = "gemini"
        elif settings.anthropic_api_key:
            provider = "anthropic"
        else:
            raise RuntimeError(
                "No LLM provider credentials are configured. Set AWS, GEMINI_API_KEY, or ANTHROPIC_API_KEY in the backend environment."
            )

    if provider == "bedrock":
        if not (settings.aws_access_key_id and settings.aws_secret_access_key):
            raise RuntimeError("Bedrock is selected but AWS credentials are missing.")
        from app.llm.bedrock import BedrockProvider

        return BedrockProvider()

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini is selected but GEMINI_API_KEY is missing.")
        from app.llm.gemini import GeminiProvider

        return GeminiProvider(model_id=settings.gemini_model_id)

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Anthropic is selected but ANTHROPIC_API_KEY is missing.")
        from app.llm.anthropic import AnthropicProvider

        return AnthropicProvider()

    raise RuntimeError(f"Unsupported llm_provider: {settings.llm_provider}")


def make_small_talk_llm() -> LLMProvider | None:
    """Create the dedicated small-talk provider when enabled and available."""
    settings = get_settings()
    if not settings.small_talk_enabled:
        return None

    if not settings.gemini_api_key:
        return None

    from app.llm.gemini import GeminiProvider

    return GeminiProvider(
        model_id=settings.gemini_small_talk_model_id,
        temperature=settings.gemini_small_talk_temperature,
        thinking_level=settings.gemini_small_talk_thinking_level,
        enable_google_search=settings.gemini_enable_google_search,
    )
