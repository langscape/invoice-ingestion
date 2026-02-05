"""Extraction API routes."""
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from ...storage.database import get_session
from ...storage.repositories import ExtractionRepo

router = APIRouter()


@router.get("")
async def list_extractions(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    commodity: str | None = None,
    confidence_tier: str | None = None,
    status: str | None = None,
    session=Depends(get_session),
):
    """List extractions with optional filters."""
    repo = ExtractionRepo(session)
    extractions = await repo.list_extractions(
        offset=offset, limit=limit,
        commodity=commodity, confidence_tier=confidence_tier, status=status,
    )
    return {
        "items": [_serialize_extraction(e) for e in extractions],
        "offset": offset,
        "limit": limit,
    }


@router.get("/{extraction_id}")
async def get_extraction(extraction_id: UUID, session=Depends(get_session)):
    """Get a single extraction result."""
    repo = ExtractionRepo(session)
    extraction = await repo.get_by_id(extraction_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return _serialize_extraction(extraction)


@router.get("/{extraction_id}/pdf")
async def get_extraction_pdf(extraction_id: UUID, session=Depends(get_session)):
    """Get SAS URL for the original PDF."""
    repo = ExtractionRepo(session)
    extraction = await repo.get_by_id(extraction_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    # In production, would generate SAS URL via BlobStorageClient
    return {"pdf_url": f"/blobs/{extraction.blob_name}"}


@router.get("/{extraction_id}/images/{page}")
async def get_extraction_image(extraction_id: UUID, page: int, session=Depends(get_session)):
    """Get SAS URL for a page image."""
    repo = ExtractionRepo(session)
    extraction = await repo.get_by_id(extraction_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return {"image_url": f"/blobs/{extraction_id}/pages/{page}.png"}


def _serialize_extraction(extraction) -> dict:
    return {
        "extraction_id": str(extraction.extraction_id),
        "file_hash": extraction.file_hash,
        "blob_name": extraction.blob_name,
        "status": extraction.status,
        "confidence_score": extraction.confidence_score,
        "confidence_tier": extraction.confidence_tier,
        "commodity_type": extraction.commodity_type,
        "utility_provider": extraction.utility_provider,
        "processing_time_ms": extraction.processing_time_ms,
        "created_at": extraction.created_at.isoformat() if extraction.created_at else None,
        "result": extraction.result_json,
    }
