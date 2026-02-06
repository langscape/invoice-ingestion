"""Log LLM calls for troubleshooting."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from ..storage.models import LLMCall


@dataclass
class LLMCallRecord:
    """Record of a single LLM call."""
    call_id: UUID = field(default_factory=uuid4)
    extraction_id: UUID | None = None
    stage: str = ""
    model: str = ""
    provider: str = ""

    # Request
    system_prompt: str | None = None
    user_prompt: str = ""
    has_images: bool = False
    image_count: int = 0
    temperature: float | None = None
    max_tokens: int | None = None

    # Response
    response_content: str | None = None
    error_message: str | None = None

    # Token usage
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    # Timing
    start_time: float = 0.0
    duration_ms: int | None = None

    def to_model(self) -> "LLMCall":
        """Convert to SQLAlchemy model."""
        from ..storage.models import LLMCall

        return LLMCall(
            call_id=self.call_id,
            extraction_id=self.extraction_id,
            stage=self.stage,
            model=self.model,
            provider=self.provider,
            system_prompt=self.system_prompt,
            user_prompt=self.user_prompt,
            has_images=self.has_images,
            image_count=self.image_count,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_content=self.response_content,
            error_message=self.error_message,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            duration_ms=self.duration_ms,
        )


class LLMCallLogger:
    """Collects LLM calls during pipeline execution."""

    def __init__(self, extraction_id: UUID | None = None):
        self.extraction_id = extraction_id
        self.calls: list[LLMCallRecord] = []
        self._current_call: LLMCallRecord | None = None

    def start_call(
        self,
        stage: str,
        model: str,
        provider: str,
        system_prompt: str | None,
        user_prompt: str,
        images: list | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCallRecord:
        """Start recording a new LLM call."""
        record = LLMCallRecord(
            extraction_id=self.extraction_id,
            stage=stage,
            model=model,
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            has_images=bool(images),
            image_count=len(images) if images else 0,
            temperature=temperature,
            max_tokens=max_tokens,
            start_time=time.monotonic(),
        )
        self._current_call = record
        return record

    def end_call(
        self,
        response_content: str | None = None,
        error_message: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ):
        """Finish recording the current LLM call."""
        if self._current_call is None:
            return

        record = self._current_call
        record.response_content = response_content
        record.error_message = error_message
        record.input_tokens = input_tokens
        record.output_tokens = output_tokens
        if input_tokens and output_tokens:
            record.total_tokens = input_tokens + output_tokens
        record.duration_ms = int((time.monotonic() - record.start_time) * 1000)

        self.calls.append(record)
        self._current_call = None

    async def save_to_database(self):
        """Save all recorded calls to the database."""
        if not self.calls:
            return

        from ..storage.database import AsyncSessionLocal
        from ..storage.repositories import LLMCallRepo

        async with AsyncSessionLocal() as session:
            repo = LLMCallRepo(session)
            for record in self.calls:
                await repo.create(record.to_model())
            await session.commit()


# Global logger instance for the current extraction
_current_logger: LLMCallLogger | None = None
_current_stage: str = ""


def get_logger() -> LLMCallLogger | None:
    """Get the current LLM call logger."""
    return _current_logger


def set_logger(logger: LLMCallLogger | None):
    """Set the current LLM call logger."""
    global _current_logger
    _current_logger = logger


def get_current_stage() -> str:
    """Get the current pipeline stage."""
    return _current_stage


def set_current_stage(stage: str):
    """Set the current pipeline stage for logging."""
    global _current_stage
    _current_stage = stage
