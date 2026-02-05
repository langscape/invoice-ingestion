"""LLM client abstract base class."""
from __future__ import annotations
from abc import ABC, abstractmethod
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Response from an LLM call."""
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = ""
    latency_ms: int = 0


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Text-only completion."""
        ...

    @abstractmethod
    async def complete_vision(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[str],  # base64-encoded images
        *,
        temperature: float = 0.0,
        max_tokens: int = 8192,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Vision completion with images."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name being used."""
        ...
