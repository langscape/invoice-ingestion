#!/usr/bin/env python3
"""Process a PDF through the extraction pipeline."""
import asyncio
import json
import sys
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
load_dotenv()

from invoice_ingestion.config import Settings
from invoice_ingestion.pipeline import ExtractionPipeline


async def main(pdf_path: str) -> None:
    """Process a single PDF and print the result."""
    path = Path(pdf_path)
    if not path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    print(f"Processing: {path.name}")
    print("-" * 50)

    settings = Settings()
    pipeline = ExtractionPipeline(settings)

    with open(path, "rb") as f:
        file_bytes = f.read()

    print(f"File size: {len(file_bytes):,} bytes")

    try:
        result = await pipeline.process(file_bytes, path.name)

        print(f"\nExtraction ID: {result.extraction_metadata.extraction_id}")
        print(f"Commodity: {result.classification.commodity_type}")
        print(f"Complexity: {result.classification.complexity_tier}")
        print(f"Confidence: {result.extraction_metadata.overall_confidence:.2%}")
        print(f"Tier: {result.extraction_metadata.confidence_tier}")
        print(f"Processing time: {result.extraction_metadata.processing_time_ms}ms")

        if result.extraction_metadata.flags:
            print(f"Flags: {', '.join(result.extraction_metadata.flags)}")

        # Print invoice details
        print(f"\nInvoice Number: {result.invoice.invoice_number.value}")
        print(f"Invoice Date: {result.invoice.invoice_date.value}")
        print(f"Due Date: {result.invoice.due_date.value}")

        # Print account details
        print(f"\nAccount: {result.account.account_number.value}")
        print(f"Customer: {result.account.customer_name.value}")
        print(f"Utility: {result.account.utility_provider.value}")

        # Save full result
        output_path = path.with_suffix(".json")
        with open(output_path, "w") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)
        print(f"\nFull result saved to: {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/process_pdf.py <path-to-pdf>")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
