#!/usr/bin/env python3
"""Import an extraction JSON file into the database."""
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from invoice_ingestion.config import Settings


async def main(json_path: str) -> None:
    """Import extraction JSON into the database."""
    path = Path(json_path)
    if not path.exists():
        print(f"Error: File not found: {json_path}")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    settings = Settings()
    engine = create_async_engine(settings.database_url.get_secret_value())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    extraction_id = data["extraction_metadata"]["extraction_id"]
    file_hash = data["extraction_metadata"]["source_document"]["file_hash"]
    confidence_score = data["extraction_metadata"]["overall_confidence"]
    confidence_tier = data["extraction_metadata"]["confidence_tier"]
    commodity_type = data["classification"]["commodity_type"]
    utility_provider = data["account"]["utility_provider"]["value"] or "Unknown"
    processing_time_ms = data["extraction_metadata"]["processing_time_ms"]

    # Determine status based on confidence tier
    if confidence_tier == "auto_accept":
        status = "accepted"
    elif confidence_tier == "targeted_review":
        status = "pending_review"
    else:
        status = "pending_review"

    async with session_factory() as session:
        # Insert extraction
        await session.execute(
            text("""
                INSERT INTO extractions
                (extraction_id, file_hash, blob_name, status, result_json,
                 confidence_score, confidence_tier, commodity_type, utility_provider, processing_time_ms,
                 created_at, updated_at)
                VALUES
                (:extraction_id, :file_hash, :blob_name, :status, :result_json,
                 :confidence_score, :confidence_tier, :commodity_type, :utility_provider, :processing_time_ms,
                 NOW(), NOW())
                ON CONFLICT (extraction_id) DO UPDATE SET
                    result_json = EXCLUDED.result_json,
                    status = EXCLUDED.status,
                    updated_at = NOW()
            """),
            {
                "extraction_id": extraction_id,
                "file_hash": file_hash,
                "blob_name": path.stem + ".pdf",
                "status": status,
                "result_json": json.dumps(data),
                "confidence_score": confidence_score,
                "confidence_tier": confidence_tier,
                "commodity_type": commodity_type,
                "utility_provider": utility_provider,
                "processing_time_ms": processing_time_ms,
            }
        )
        await session.commit()

    await engine.dispose()

    print(f"Imported extraction: {extraction_id}")
    print(f"  Commodity: {commodity_type}")
    print(f"  Confidence: {confidence_score:.0%} ({confidence_tier})")
    print(f"  Status: {status}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_extraction.py <path-to-json>")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
