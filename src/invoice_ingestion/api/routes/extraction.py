"""Extraction API routes."""
from __future__ import annotations
import base64
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from ...storage.database import get_session
from ...storage.repositories import ExtractionRepo
from ...config import Settings

router = APIRouter()


def get_settings() -> Settings:
    return Settings()


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
async def get_extraction_pdf(
    extraction_id: UUID,
    session=Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """Get the original PDF file.

    For local development, serves from local storage path.
    For production, would return a SAS URL to Azure Blob Storage.
    """
    repo = ExtractionRepo(session)
    extraction = await repo.get_by_id(extraction_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    # Try local storage first (for development)
    local_path = Path(settings.local_storage_path) / "pdfs" / f"{extraction_id}.pdf"
    if local_path.exists():
        return FileResponse(
            local_path,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    # Fallback: check if blob_name points to a local file
    if extraction.blob_name:
        blob_path = Path(extraction.blob_name)
        if blob_path.exists():
            return FileResponse(
                blob_path,
                media_type="application/pdf",
                filename=blob_path.name,
            )

    # Production: would generate SAS URL via BlobStorageClient
    raise HTTPException(
        status_code=404,
        detail="PDF not found. Ensure local_storage_path is configured or blob storage is available."
    )


@router.get("/{extraction_id}/images/{page}")
async def get_extraction_image(
    extraction_id: UUID,
    page: int,
    session=Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """Get a rendered page image.

    For local development, serves from local storage path.
    For production, would return a SAS URL to Azure Blob Storage.
    """
    repo = ExtractionRepo(session)
    extraction = await repo.get_by_id(extraction_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    # Try local storage first (for development)
    local_path = Path(settings.local_storage_path) / "images" / str(extraction_id) / f"page_{page:03d}.png"
    if local_path.exists():
        return FileResponse(
            local_path,
            media_type="image/png",
            filename=f"page_{page}.png",
        )

    # Fallback: check result_json for base64 images (stored during extraction)
    if extraction.result_json:
        pages_data = extraction.result_json.get("_page_images", [])
        if 0 < page <= len(pages_data):
            image_b64 = pages_data[page - 1]
            if image_b64:
                # Decode base64 and return as image
                image_bytes = base64.b64decode(image_b64)
                return Response(
                    content=image_bytes,
                    media_type="image/png",
                    headers={"Content-Disposition": f"inline; filename=page_{page}.png"},
                )

    # Production: would generate SAS URL via BlobStorageClient
    raise HTTPException(
        status_code=404,
        detail=f"Image for page {page} not found. Ensure images are stored during extraction."
    )


def _serialize_extraction(extraction) -> dict:
    result = extraction.result_json or {}
    # Remove internal fields from API response
    if "_page_images" in result:
        result = {k: v for k, v in result.items() if k != "_page_images"}

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
        "result": result,
    }
