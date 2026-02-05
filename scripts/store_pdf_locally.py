#!/usr/bin/env python3
"""Store a PDF file in local storage for the review UI.

Usage:
    python scripts/store_pdf_locally.py <extraction_id> <pdf_path>

This copies the PDF to ./data/pdfs/{extraction_id}.pdf so the review UI can display it.
"""
import shutil
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python scripts/store_pdf_locally.py <extraction_id> <pdf_path>")
        print()
        print("Example:")
        print("  python scripts/store_pdf_locally.py c2ebeed5-e849-47a8-acf4-7ebfc27967a6 ~/Downloads/invoice.pdf")
        sys.exit(1)

    extraction_id = sys.argv[1]
    pdf_path = Path(sys.argv[2]).expanduser()

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    # Create local storage directory
    data_dir = Path("./data/pdfs")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Copy PDF
    dest_path = data_dir / f"{extraction_id}.pdf"
    shutil.copy(pdf_path, dest_path)

    print(f"Stored PDF at: {dest_path}")
    print(f"The review UI at http://localhost:3000/review/{extraction_id} should now display the PDF.")


if __name__ == "__main__":
    main()
