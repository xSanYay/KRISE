"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Interface for LLM providers (Bedrock, direct API, etc.)."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        """Generate a text response from the LLM."""
        ...

    @abstractmethod
    async def generate_json(self, prompt: str, system: str = "", max_tokens: int = 2048) -> dict[str, Any]:
        """Generate a JSON response from the LLM, parsed into a dict."""
        ...
