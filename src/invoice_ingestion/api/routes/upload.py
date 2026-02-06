"""Upload API route for local testing."""
from __future__ import annotations
import os
import traceback
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Request
import structlog

# Load .env for local development
from dotenv import load_dotenv
load_dotenv()

from ...config import Settings
from ...pipeline import ExtractionPipeline

router = APIRouter()
logger = structlog.get_logger(__name__)

# Store processing status
_processing_status: dict[str, dict] = {}


async def _process_invoice(file_bytes: bytes, filename: str, job_id: str):
    """Background task to process uploaded invoice."""
    try:
        _processing_status[job_id] = {"status": "processing", "filename": filename}
        logger.info("upload_processing_start", job_id=job_id, filename=filename)

        # Load settings fresh (with env vars from .env)
        settings = Settings()

        pipeline = ExtractionPipeline(settings)
        result = await pipeline.process(file_bytes, filename)

        _processing_status[job_id] = {
            "status": "completed",
            "filename": filename,
            "extraction_id": str(result.extraction_metadata.extraction_id),
            "confidence": result.extraction_metadata.overall_confidence,
            "confidence_tier": result.extraction_metadata.confidence_tier.value,
        }
        logger.info("upload_processing_complete", job_id=job_id, extraction_id=str(result.extraction_metadata.extraction_id))
    except Exception as e:
        logger.error("upload_processing_failed", job_id=job_id, error=str(e), traceback=traceback.format_exc())
        _processing_status[job_id] = {
            "status": "failed",
            "filename": filename,
            "error": str(e),
        }


@router.post("/")
async def upload_invoice(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload a PDF invoice for processing.

    Returns a job_id to check processing status.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read file content
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    # Generate job ID
    job_id = str(uuid4())

    # Start background processing
    _processing_status[job_id] = {"status": "queued", "filename": file.filename}
    background_tasks.add_task(_process_invoice, file_bytes, file.filename, job_id)

    logger.info("upload_queued", job_id=job_id, filename=file.filename, size_bytes=len(file_bytes))

    return {
        "job_id": job_id,
        "filename": file.filename,
        "status": "queued",
        "message": "Invoice queued for processing",
    }


@router.get("/status/{job_id}")
async def get_upload_status(job_id: str):
    """Check the status of an uploaded invoice."""
    if job_id not in _processing_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return _processing_status[job_id]


@router.get("/jobs")
async def list_jobs():
    """List all processing jobs."""
    return {"jobs": list(_processing_status.values())}


@router.post("/reprocess/{extraction_id}")
async def reprocess_invoice(
    extraction_id: str,
    background_tasks: BackgroundTasks,
):
    """Reprocess an existing invoice.

    Useful after editing correction rules to see updated extraction results.
    """
    from uuid import UUID
    from ...storage.database import AsyncSessionLocal
    from ...storage.repositories import ExtractionRepo

    # Load the extraction to get the PDF path
    async with AsyncSessionLocal() as session:
        repo = ExtractionRepo(session)
        try:
            extraction = await repo.get_by_id(UUID(extraction_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid extraction ID")

        if not extraction:
            raise HTTPException(status_code=404, detail="Extraction not found")

    # Load settings to get local storage path
    settings = Settings()

    # Find the PDF file
    pdf_path = Path(settings.local_storage_path) / "pdfs" / f"{extraction_id}.pdf"

    if not pdf_path.exists():
        # Try blob_name as fallback
        if extraction.blob_name and Path(extraction.blob_name).exists():
            pdf_path = Path(extraction.blob_name)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"PDF file not found at {pdf_path}. Cannot reprocess."
            )

    # Read the PDF
    file_bytes = pdf_path.read_bytes()

    # Generate job ID
    job_id = str(uuid4())
    filename = f"reprocess_{extraction.blob_name or extraction_id}"

    # Start background processing
    _processing_status[job_id] = {
        "status": "queued",
        "filename": filename,
        "reprocess_of": extraction_id,
    }
    background_tasks.add_task(_process_invoice, file_bytes, filename, job_id)

    logger.info("reprocess_queued", job_id=job_id, extraction_id=extraction_id)

    return {
        "job_id": job_id,
        "extraction_id": extraction_id,
        "status": "queued",
        "message": "Invoice queued for reprocessing",
    }
