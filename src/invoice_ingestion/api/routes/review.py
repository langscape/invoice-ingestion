"""Review queue API routes."""
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from ...storage.database import get_session
from ...storage.repositories import ExtractionRepo, CorrectionRepo
from ...storage.models import Correction

router = APIRouter()


class CorrectionInput(BaseModel):
    field_path: str
    extracted_value: str | None = None
    corrected_value: str
    correction_type: str = "value_change"
    correction_reason: str | None = None


class CorrectionsSubmission(BaseModel):
    corrections: list[CorrectionInput]
    corrector_id: str | None = None


@router.get("/queue")
async def get_review_queue(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session=Depends(get_session),
):
    """Get extractions pending human review, sorted by priority (lowest confidence first)."""
    repo = ExtractionRepo(session)
    extractions = await repo.list_pending_review(offset=offset, limit=limit)
    return {
        "items": [
            {
                "extraction_id": str(e.extraction_id),
                "blob_name": e.blob_name,
                "confidence_score": e.confidence_score,
                "confidence_tier": e.confidence_tier,
                "commodity_type": e.commodity_type,
                "utility_provider": e.utility_provider,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "status": e.status,
            }
            for e in extractions
        ],
        "offset": offset,
        "limit": limit,
    }


@router.get("/queue/stats")
async def get_queue_stats(session=Depends(get_session)):
    """Get review queue statistics."""
    repo = ExtractionRepo(session)
    counts = await repo.count_by_tier()
    return {"counts_by_tier": counts}


@router.post("/{extraction_id}/corrections")
async def submit_corrections(
    extraction_id: UUID,
    submission: CorrectionsSubmission,
    session=Depends(get_session),
):
    """Submit corrections for an extraction."""
    extraction_repo = ExtractionRepo(session)
    extraction = await extraction_repo.get_by_id(extraction_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    correction_repo = CorrectionRepo(session)
    created = []
    for c in submission.corrections:
        correction = Correction(
            extraction_id=extraction_id,
            field_path=c.field_path,
            extracted_value=c.extracted_value,
            corrected_value=c.corrected_value,
            correction_type=c.correction_type,
            correction_reason=c.correction_reason,
            corrector_id=submission.corrector_id,
            invoice_context_json={
                "utility": extraction.utility_provider,
                "commodity": extraction.commodity_type,
            },
        )
        correction = await correction_repo.create(correction)
        created.append(str(correction.correction_id))

    # Update extraction status
    await extraction_repo.update_status(extraction_id, "reviewed")
    await session.commit()

    return {"correction_ids": created, "count": len(created)}


@router.post("/{extraction_id}/approve")
async def approve_extraction(extraction_id: UUID, session=Depends(get_session)):
    """Approve an extraction (no corrections needed)."""
    repo = ExtractionRepo(session)
    extraction = await repo.get_by_id(extraction_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    await repo.update_status(extraction_id, "accepted")
    await session.commit()
    return {"status": "accepted"}


@router.post("/{extraction_id}/approve-all-green")
async def approve_all_green(extraction_id: UUID, session=Depends(get_session)):
    """Approve all fields with confidence >= 0.90."""
    repo = ExtractionRepo(session)
    extraction = await repo.get_by_id(extraction_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    # Mark as accepted if overall confidence is high enough
    if extraction.confidence_score and extraction.confidence_score >= 0.90:
        await repo.update_status(extraction_id, "accepted")
        await session.commit()
        return {"status": "accepted", "message": "All fields above threshold"}

    return {"status": "partial", "message": "Some fields below threshold, requires manual review"}
