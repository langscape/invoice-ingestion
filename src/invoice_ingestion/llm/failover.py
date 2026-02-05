"""Failover LLM client that tries primary then falls back."""
from __future__ import annotations
import structlog
from .base import LLMClient, LLMResponse

logger = structlog.get_logger(__name__)


class FailoverLLMClient(LLMClient):
    """Wraps two LLM clients. Tries primary; on failure falls back to secondary."""

    def __init__(self, primary: LLMClient, fallback: LLMClient):
        self._primary = primary
        self._fallback = fallback
        self._failover_count = 0

    async def complete_text(self, system_prompt, user_prompt, *, temperature=0.0, max_tokens=4096, json_mode=False) -> LLMResponse:
        try:
            return await self._primary.complete_text(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)
        except Exception as e:
            logger.warning("primary_llm_failed", error=str(e), model=self._primary.get_model_name())
            self._failover_count += 1
            return await self._fallback.complete_text(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)

    async def complete_vision(self, system_prompt, user_prompt, images, *, temperature=0.0, max_tokens=8192, json_mode=False) -> LLMResponse:
        try:
            return await self._primary.complete_vision(system_prompt, user_prompt, images, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)
        except Exception as e:
            logger.warning("primary_llm_vision_failed", error=str(e), model=self._primary.get_model_name())
            self._failover_count += 1
            return await self._fallback.complete_vision(system_prompt, user_prompt, images, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)

    def get_model_name(self) -> str:
        return f"{self._primary.get_model_name()} (failover: {self._fallback.get_model_name()})"

    @property
    def failover_count(self) -> int:
        return self._failover_count
