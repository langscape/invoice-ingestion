"""Anthropic Claude LLM client — supports Azure AI Foundry deployments."""
from __future__ import annotations

import asyncio
import time

import anthropic
import structlog

from .base import LLMClient, LLMResponse
from .call_logger import get_logger

logger = structlog.get_logger(__name__)

# Default retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 2.0, 4.0]

# Exceptions that are retryable
RETRYABLE_EXCEPTIONS = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    anthropic.APIStatusError,
)


class AnthropicClient(LLMClient):
    """LLM client for Claude models deployed via Azure AI Foundry.

    When ``azure_endpoint`` is provided, the client connects to the Azure AI
    Model Catalog serverless deployment instead of the Anthropic API directly.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        timeout: int = 120,
        azure_endpoint: str | None = None,
    ):
        self._model = model
        self._timeout = timeout

        if azure_endpoint:
            # Azure AI Foundry: Claude models are deployed as serverless APIs
            # that expose an Anthropic-compatible Messages endpoint.
            self._client = anthropic.AsyncAnthropic(
                api_key=api_key,
                base_url=f"{azure_endpoint.rstrip('/')}",
                timeout=float(timeout),
            )
            self._provider = "azure_ai"
        else:
            self._client = anthropic.AsyncAnthropic(
                api_key=api_key,
                timeout=float(timeout),
            )
            self._provider = "anthropic"

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Text-only completion using the Anthropic Messages API."""
        messages = [{"role": "user", "content": user_prompt}]

        if json_mode:
            if not system_prompt.rstrip().endswith("Respond with valid JSON only."):
                system_prompt = system_prompt.rstrip() + "\n\nRespond with valid JSON only."

        return await self._call_with_retry(
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def complete_vision(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[str],
        *,
        temperature: float = 0.0,
        max_tokens: int = 8192,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Vision completion with base64-encoded images."""
        content: list[dict] = []

        # Add image blocks first
        for base64_str in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64_str,
                },
            })

        # Add text block
        content.append({"type": "text", "text": user_prompt})

        messages = [{"role": "user", "content": content}]

        if json_mode:
            if not system_prompt.rstrip().endswith("Respond with valid JSON only."):
                system_prompt = system_prompt.rstrip() + "\n\nRespond with valid JSON only."

        return await self._call_with_retry(
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def get_model_name(self) -> str:
        """Return the model name being used."""
        return f"{self._model} ({self._provider})"

    async def _call_with_retry(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call the Anthropic API with exponential backoff retries."""
        last_exception: Exception | None = None

        # Extract user prompt and images for logging
        user_prompt = ""
        images: list = []
        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, str):
                    user_prompt = content
                elif isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            user_prompt = item.get("text", "")
                        elif item.get("type") == "image":
                            images.append(item)

        # Start logging
        call_logger = get_logger()
        if call_logger:
            from .call_logger import get_current_stage
            call_logger.start_call(
                stage=get_current_stage(),
                model=self._model,
                provider=self._provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                images=images,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        for attempt in range(MAX_RETRIES + 1):
            try:
                start = time.monotonic()
                response = await self._client.messages.create(
                    model=self._model,
                    system=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)

                # Extract content text from response
                content_text = ""
                for block in response.content:
                    if block.type == "text":
                        content_text += block.text

                # Log successful call
                if call_logger:
                    call_logger.end_call(
                        response_content=content_text,
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                    )

                return LLMResponse(
                    content=content_text,
                    model=response.model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    finish_reason=response.stop_reason or "",
                    latency_ms=elapsed_ms,
                )

            except RETRYABLE_EXCEPTIONS as exc:
                last_exception = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        "anthropic_api_retry",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(exc),
                        model=self._model,
                        provider=self._provider,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "anthropic_api_exhausted_retries",
                        attempts=MAX_RETRIES + 1,
                        error=str(exc),
                        model=self._model,
                        provider=self._provider,
                    )
                    # Log failed call
                    if call_logger:
                        call_logger.end_call(error_message=str(exc))

        raise last_exception  # type: ignore[misc]
