"""Pass 0: Ingestion & Pre-Processing -- pure code, no LLM."""
from __future__ import annotations

import structlog

from ..models.internal import IngestionResult, PageData
from ..utils.hashing import compute_file_hash
from ..utils.pdf import (
    render_pdf_to_images,
    extract_text_pymupdf,
    detect_file_type,
    extract_pdf_attachments,
)
from ..utils.image import compute_quality_score, image_to_base64
from ..international.structured_invoice import check_structured_invoice

logger = structlog.get_logger(__name__)


def _detect_language(text: str) -> str:
    """Detect language of text using langdetect, defaulting to 'en'."""
    if not text or not text.strip():
        return "en"
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return "en"


def run_pass0(file_bytes: bytes, dpi: int = 300) -> IngestionResult:
    """Run Pass 0: Ingestion & Pre-Processing.

    Steps:
    1. Detect file type from magic bytes
    2. Compute SHA-256 hash for deduplication
    3. Render PDF pages as images at configurable DPI
    4. Extract text from each page via PyMuPDF
    5. Compute image quality score per page
    6. Detect language from extracted text
    7. Check for structured invoice attachments (Factur-X, etc.)
    8. Compute overall image quality (average of page scores)
    9. Build and return IngestionResult
    """
    # Step 1: Detect file type
    file_type = detect_file_type(file_bytes)
    logger.info("pass0_file_type_detected", file_type=file_type)

    # Step 2: Compute SHA-256 hash
    file_hash = compute_file_hash(file_bytes)
    logger.info("pass0_file_hash_computed", file_hash=file_hash[:16])

    pages: list[PageData] = []

    if file_type == "pdf":
        # Step 3: Render pages as images
        page_images = render_pdf_to_images(file_bytes, dpi=dpi)
        logger.info("pass0_pages_rendered", page_count=len(page_images), dpi=dpi)

        # Step 4: Extract text from each page
        page_texts = extract_text_pymupdf(file_bytes)

        # Pad page_texts if it has fewer entries than images (shouldn't happen, but safety)
        while len(page_texts) < len(page_images):
            page_texts.append("")

        # Step 5 & 6: Build PageData for each page
        for i, img_bytes in enumerate(page_images):
            quality = compute_quality_score(img_bytes)
            b64 = image_to_base64(img_bytes)
            text = page_texts[i] if i < len(page_texts) else ""
            lang = _detect_language(text)

            pages.append(PageData(
                page_number=i + 1,
                image_base64=b64,
                extracted_text=text if text.strip() else None,
                language=lang,
                quality_score=quality,
            ))

        # Step 7: Check for structured invoice attachments
        structured = check_structured_invoice(file_bytes)
        if structured:
            logger.info("pass0_structured_invoice_found", format=structured.get("format"))

    elif file_type in ("png", "jpeg", "tiff"):
        # Single image file: treat as one page
        quality = compute_quality_score(file_bytes)
        b64 = image_to_base64(file_bytes)

        pages.append(PageData(
            page_number=1,
            image_base64=b64,
            extracted_text=None,
            language="en",
            quality_score=quality,
        ))

    else:
        logger.warning("pass0_unsupported_file_type", file_type=file_type)
        # Still create a minimal result
        pages.append(PageData(
            page_number=1,
            image_base64="",
            extracted_text=None,
            language="en",
            quality_score=0.0,
        ))

    # Step 8: Compute overall image quality (average of page scores)
    if pages:
        overall_quality = sum(p.quality_score for p in pages) / len(pages)
    else:
        overall_quality = 0.0

    # Step 6 (global): Detect language from all extracted text
    all_text = " ".join(p.extracted_text or "" for p in pages)
    language_detected = _detect_language(all_text)

    logger.info(
        "pass0_complete",
        page_count=len(pages),
        overall_quality=round(overall_quality, 3),
        language=language_detected,
    )

    # Step 9: Build and return IngestionResult
    return IngestionResult(
        file_hash=file_hash,
        file_type=file_type,
        image_quality_score=round(overall_quality, 3),
        pages=pages,
        language_detected=language_detected,
    )
