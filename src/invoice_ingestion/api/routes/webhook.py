"""Webhook endpoint for blob trigger backup."""
from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


class BlobTriggerPayload(BaseModel):
    blob_name: str
    container: str = "imported"
    content_length: int | None = None


@router.post("/blob-trigger")
async def blob_trigger(payload: BlobTriggerPayload, request: Request):
    """Backup trigger endpoint for blob processing.

    Called by Azure Function or external systems when a new PDF
    is uploaded to the imported container.
    """
    logger.info("blob_trigger_received", blob_name=payload.blob_name, container=payload.container)

    settings = request.app.state.settings

    # In production, this would download the blob and invoke the pipeline
    # For now, return acknowledgment
    return {
        "status": "accepted",
        "blob_name": payload.blob_name,
        "message": "Blob processing queued",
    }
