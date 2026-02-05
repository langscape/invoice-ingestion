"""Health check endpoint."""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok", "service": "invoice-ingestion-api"}
