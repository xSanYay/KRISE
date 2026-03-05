"""Direct Anthropic API LLM provider."""

from __future__ import annotations
import json
import asyncio
from typing import Any

import httpx
import structlog

from app.llm.base import LLMProvider
from app.config import get_settings

logger = structlog.get_logger()

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(LLMProvider):
    """Direct Anthropic API provider (uses API key, not AWS Bedrock)."""

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.anthropic_api_key
        self._model = settings.anthropic_model_id
        self._client = httpx.AsyncClient(timeout=60.0)

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        response = await self._client.post(ANTHROPIC_API_URL, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()

        text = result["content"][0]["text"]

        logger.info(
            "anthropic_invoke",
            model=self._model,
            input_tokens=result.get("usage", {}).get("input_tokens"),
            output_tokens=result.get("usage", {}).get("output_tokens"),
        )
        return text

    async def generate_json(self, prompt: str, system: str = "", max_tokens: int = 2048) -> dict[str, Any]:
        text = await self.generate(prompt, system, max_tokens)
        text = text.strip()

        # Handle markdown code blocks
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
            # Try array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            logger.error("json_parse_failed", response_preview=text[:200])
            return {"error": "Failed to parse JSON", "raw": text[:500]}
