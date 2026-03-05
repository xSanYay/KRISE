"""AWS Bedrock LLM provider using Claude models."""

from __future__ import annotations
import json
import asyncio
from typing import Any

import boto3
import structlog

from app.llm.base import LLMProvider
from app.config import get_settings

logger = structlog.get_logger()


class BedrockProvider(LLMProvider):
    """AWS Bedrock Claude provider."""

    def __init__(self):
        settings = get_settings()
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_default_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self._model_id = settings.bedrock_model_id

    def _invoke(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        """Synchronous invoke using Bedrock Converse API (cross-model compatible)."""
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        
        kwargs = {
            "modelId": self._model_id,
            "messages": messages,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.7}
        }
        
        if system:
            kwargs["system"] = [{"text": system}]

        response = self._client.converse(**kwargs)
        
        text = response['output']['message']['content'][0]['text']
        usage = response.get('usage', {})

        logger.info(
            "bedrock_invoke",
            model=self._model_id,
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
        )
        return text

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        """Generate text response via Bedrock (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._invoke, prompt, system, max_tokens)

    async def generate_json(self, prompt: str, system: str = "", max_tokens: int = 2048) -> dict[str, Any]:
        """Generate and parse JSON response."""
        text = await self.generate(prompt, system, max_tokens)

        # Try to extract JSON from the response
        text = text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            logger.error("json_parse_failed", response_preview=text[:200])
            return {"error": "Failed to parse JSON", "raw": text[:500]}
