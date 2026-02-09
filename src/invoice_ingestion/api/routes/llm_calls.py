"""LLM calls API routes for troubleshooting."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ...storage.database import get_session
from ...storage.repositories import LLMCallRepo

router = APIRouter()

# Per-model pricing (USD per 1K tokens) — Azure-deployed models
# Prices reflect Azure AI Foundry / Azure OpenAI pricing as of 2026-02.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.0100},
    "gpt-4o-mini": {"input": 0.000150, "output": 0.000600},
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
}

# Fallback for unknown models
_DEFAULT_PRICING = {"input": 0.003, "output": 0.015}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated cost in USD for the given token counts."""
    pricing = MODEL_PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000


@router.get("")
async def list_llm_calls(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    extraction_id: UUID | None = None,
    stage: str | None = None,
    model: str | None = None,
    session=Depends(get_session),
):
    """List LLM calls with optional filters."""
    repo = LLMCallRepo(session)
    calls = await repo.list_calls(
        offset=offset,
        limit=limit,
        extraction_id=extraction_id,
        stage=stage,
        model=model,
    )
    return {
        "items": [_serialize_call(c) for c in calls],
        "offset": offset,
        "limit": limit,
    }


@router.get("/stats")
async def get_llm_stats(
    extraction_id: UUID | None = None,
    session=Depends(get_session),
):
    """Get aggregate stats about LLM calls.

    Pass ``extraction_id`` to scope stats to a single extraction.
    """
    repo = LLMCallRepo(session)
    stats = await repo.get_stats(extraction_id=extraction_id)

    # Enrich by_model with estimated cost
    total_cost = 0.0
    for model, data in stats["by_model"].items():
        cost = _estimate_cost(model, data["input_tokens"], data["output_tokens"])
        data["estimated_cost"] = round(cost, 6)
        total_cost += cost

    stats["total_estimated_cost"] = round(total_cost, 4)
    return stats


@router.get("/by-extraction/{extraction_id}")
async def get_calls_by_extraction(
    extraction_id: UUID,
    session=Depends(get_session),
):
    """Get all LLM calls for a specific extraction."""
    repo = LLMCallRepo(session)
    calls = await repo.get_by_extraction(extraction_id)
    return {
        "extraction_id": str(extraction_id),
        "calls": [_serialize_call(c) for c in calls],
    }


@router.get("/{call_id}")
async def get_llm_call(call_id: UUID, session=Depends(get_session)):
    """Get a single LLM call with full details."""
    repo = LLMCallRepo(session)
    # Use list_calls with a filter would work but let's add a get_by_id method
    calls = await repo.list_calls(limit=1)
    # For now, iterate to find
    stmt_calls = await repo.list_calls(limit=1000)
    call = next((c for c in stmt_calls if c.call_id == call_id), None)
    if not call:
        raise HTTPException(status_code=404, detail="LLM call not found")
    return _serialize_call_full(call)


def _serialize_call(call) -> dict:
    """Serialize LLM call for list view (truncated content)."""
    return {
        "call_id": str(call.call_id),
        "extraction_id": str(call.extraction_id) if call.extraction_id else None,
        "stage": call.stage,
        "model": call.model,
        "provider": call.provider,
        "has_images": call.has_images,
        "image_count": call.image_count,
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
        "total_tokens": call.total_tokens,
        "duration_ms": call.duration_ms,
        "error_message": call.error_message,
        "created_at": call.created_at.isoformat() if call.created_at else None,
        # Truncated preview
        "system_prompt_preview": (call.system_prompt[:200] + "...") if call.system_prompt and len(call.system_prompt) > 200 else call.system_prompt,
        "user_prompt_preview": (call.user_prompt[:200] + "...") if call.user_prompt and len(call.user_prompt) > 200 else call.user_prompt,
        "response_preview": (call.response_content[:200] + "...") if call.response_content and len(call.response_content) > 200 else call.response_content,
    }


def _serialize_call_full(call) -> dict:
    """Serialize LLM call with full content."""
    return {
        "call_id": str(call.call_id),
        "extraction_id": str(call.extraction_id) if call.extraction_id else None,
        "stage": call.stage,
        "model": call.model,
        "provider": call.provider,
        "has_images": call.has_images,
        "image_count": call.image_count,
        "temperature": call.temperature,
        "max_tokens": call.max_tokens,
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
        "total_tokens": call.total_tokens,
        "duration_ms": call.duration_ms,
        "error_message": call.error_message,
        "created_at": call.created_at.isoformat() if call.created_at else None,
        # Full content
        "system_prompt": call.system_prompt,
        "user_prompt": call.user_prompt,
        "response_content": call.response_content,
    }
