"""Blob processor worker: download → pipeline → store."""
from __future__ import annotations
import asyncio
import structlog
from ..config import Settings
from ..pipeline import ExtractionPipeline
from ..storage.database import init_db, get_session
from ..storage.models import Extraction
from ..storage.repositories import ExtractionRepo
from ..utils.hashing import compute_file_hash

logger = structlog.get_logger(__name__)


async def process_blob(blob_name: str, file_bytes: bytes, settings: Settings) -> dict:
    """Process a single blob through the extraction pipeline.

    Steps:
    1. Check dedup (file hash)
    2. Run pipeline
    3. Store result
    4. Return result summary
    """
    file_hash = compute_file_hash(file_bytes)

    # Check for existing extraction with same hash
    init_db(settings.database_url)
    async for session in get_session():
        repo = ExtractionRepo(session)
        existing = await repo.get_by_hash(file_hash)
        if existing and existing.status in ("accepted", "pending_review"):
            logger.info("dedup_hit", file_hash=file_hash, extraction_id=str(existing.extraction_id))
            return {"status": "duplicate", "extraction_id": str(existing.extraction_id)}

        # Create extraction record
        extraction_record = Extraction(
            file_hash=file_hash,
            blob_name=blob_name,
            status="processing",
        )
        extraction_record = await repo.create(extraction_record)
        await session.commit()
        extraction_id = extraction_record.extraction_id

    # Run pipeline
    pipeline = ExtractionPipeline(settings)
    try:
        result = await pipeline.process(file_bytes, blob_name)

        # Update DB with result
        async for session in get_session():
            repo = ExtractionRepo(session)
            status = "accepted" if result.extraction_metadata.confidence_tier == "auto_accept" else "pending_review"
            await repo.update_result(
                extraction_id=extraction_id,
                result_json=result.model_dump(mode="json"),
                confidence_score=result.extraction_metadata.overall_confidence,
                confidence_tier=result.extraction_metadata.confidence_tier,
            )
            await repo.update_status(extraction_id, status)
            await session.commit()

        logger.info("extraction_complete", extraction_id=str(extraction_id),
                    confidence=result.extraction_metadata.overall_confidence,
                    tier=result.extraction_metadata.confidence_tier)

        return {
            "status": "completed",
            "extraction_id": str(extraction_id),
            "confidence": result.extraction_metadata.overall_confidence,
            "tier": result.extraction_metadata.confidence_tier,
        }

    except Exception as e:
        logger.error("pipeline_failed", extraction_id=str(extraction_id), error=str(e))
        async for session in get_session():
            repo = ExtractionRepo(session)
            await repo.update_status(extraction_id, "failed")
            await session.commit()
        raise


def main():
    """Entry point for worker process."""
    import sys
    settings = Settings()
    logger.info("worker_started")

    # In production, this would listen for queue messages or blob events
    # For now, just a placeholder that can be invoked directly
    if len(sys.argv) > 1:
        blob_name = sys.argv[1]
        with open(blob_name, "rb") as f:
            file_bytes = f.read()
        asyncio.run(process_blob(blob_name, file_bytes, settings))
    else:
        logger.info("worker_idle", message="No blob specified. Waiting for events...")


if __name__ == "__main__":
    main()
