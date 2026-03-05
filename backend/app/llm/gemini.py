"""Google Gemini LLM provider."""

from __future__ import annotations
import json
import asyncio
from typing import Any
import structlog

from google import genai
from google.genai import types

from app.llm.base import LLMProvider
from app.config import get_settings

logger = structlog.get_logger()

class GeminiProvider(LLMProvider):
    """Google Gemini API Provider."""

    def __init__(self):
        settings = get_settings()
        # Initialize client with API key explicitly (though it also reads GEMINI_API_KEY from env)
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model_id

    def _invoke(self, prompt: str, system: str = "", max_tokens: int = 2048, response_mime_type: str = "text/plain") -> str:
        config = types.GenerateContentConfig(
            system_instruction=system if system else None,
            max_output_tokens=max_tokens,
            response_mime_type=response_mime_type,
            temperature=0.7,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return response.text

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, self._invoke, prompt, system, max_tokens, "text/plain")
        logger.info("gemini_invoke", model=self._model)
        return text

    async def generate_json(self, prompt: str, system: str = "", max_tokens: int = 2048) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        # Enforce JSON output using application/json
        text = await loop.run_in_executor(None, self._invoke, prompt, system, max_tokens, "application/json")
        text = text.strip()

        logger.info("gemini_invoke_json", model=self._model)

        # Handle markdown code blocks just in case
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            logger.error("json_parse_failed", response_preview=text[:200])
            return {"error": "Failed to parse JSON", "raw": text[:500]}
