"""OpenAI LLM client — uses Azure OpenAI deployments."""
from __future__ import annotations

import asyncio
import time

import openai
import structlog

from .base import LLMClient, LLMResponse
from .call_logger import get_logger

logger = structlog.get_logger(__name__)

# Default retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 2.0, 4.0]

# Exceptions that are retryable
RETRYABLE_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
    openai.APIStatusError,
)


class OpenAIClient(LLMClient):
    """LLM client for GPT models deployed via Azure OpenAI Service.

    Always connects to Azure OpenAI. The ``azure_endpoint`` and ``api_key``
    point to an Azure OpenAI resource, and ``model`` is the deployment name.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        azure_endpoint: str = "",
        timeout: int = 120,
    ):
        self._model = model
        self._timeout = timeout

        if not azure_endpoint:
            raise ValueError(
                "azure_endpoint is required — GPT models must be accessed "
                "via Azure OpenAI Service."
            )

        self._client = openai.AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version="2024-06-01",
            timeout=float(timeout),
        )

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Text-only completion using the Azure OpenAI Chat Completions API."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: dict = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        return await self._call_with_retry(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
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
        # Build user content with images and text
        user_content: list[dict] = []

        for base64_str in images:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_str}",
                    "detail": "high",
                },
            })

        user_content.append({"type": "text", "text": user_prompt})

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        kwargs: dict = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        return await self._call_with_retry(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def get_model_name(self) -> str:
        """Return the model name being used."""
        return f"{self._model} (azure_openai)"

    async def _call_with_retry(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> LLMResponse:
        """Call the Azure OpenAI API with exponential backoff retries."""
        last_exception: Exception | None = None

        # Extract prompts for logging
        system_prompt = ""
        user_prompt = ""
        images: list = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
            elif msg["role"] == "user":
                if isinstance(msg["content"], str):
                    user_prompt = msg["content"]
                elif isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item.get("type") == "text":
                            user_prompt = item.get("text", "")
                        elif item.get("type") == "image_url":
                            images.append(item)

        # Start logging
        call_logger = get_logger()
        if call_logger:
            from .call_logger import get_current_stage
            call_logger.start_call(
                stage=get_current_stage(),
                model=self._model,
                provider="azure_openai",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                images=images,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        for attempt in range(MAX_RETRIES + 1):
            try:
                start = time.monotonic()
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)

                choice = response.choices[0]
                content_text = choice.message.content or ""

                input_tokens = 0
                output_tokens = 0
                if response.usage is not None:
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens

                # Log successful call
                if call_logger:
                    call_logger.end_call(
                        response_content=content_text,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )

                return LLMResponse(
                    content=content_text,
                    model=response.model or self._model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    finish_reason=choice.finish_reason or "",
                    latency_ms=elapsed_ms,
                )

            except RETRYABLE_EXCEPTIONS as exc:
                last_exception = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        "azure_openai_api_retry",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(exc),
                        model=self._model,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "azure_openai_api_exhausted_retries",
                        attempts=MAX_RETRIES + 1,
                        error=str(exc),
                        model=self._model,
                    )
                    # Log failed call
                    if call_logger:
                        call_logger.end_call(error_message=str(exc))

        raise last_exception  # type: ignore[misc]
