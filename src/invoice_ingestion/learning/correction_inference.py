"""Auto-infer correction categories from patterns."""
from __future__ import annotations

import re

# Correction categories
CATEGORY_OCR_ERROR = "ocr_error"
CATEGORY_FORMAT_NORMALIZE = "format_normalize"
CATEGORY_WRONG_ON_DOCUMENT = "wrong_on_document"
CATEGORY_MISSING_CONTEXT = "missing_context"
CATEGORY_CALCULATION_ERROR = "calculation_error"
CATEGORY_OTHER = "other"

# Human-readable descriptions for each category
CATEGORY_DESCRIPTIONS = {
    CATEGORY_OCR_ERROR: "OCR misread characters (e.g., 0/O, 1/l confusion)",
    CATEGORY_FORMAT_NORMALIZE: "Format standardization (trailing characters, spacing)",
    CATEGORY_WRONG_ON_DOCUMENT: "The document itself contains an error",
    CATEGORY_MISSING_CONTEXT: "LLM missed context that changes interpretation",
    CATEGORY_CALCULATION_ERROR: "Mathematical or calculation error",
    CATEGORY_OTHER: "Other correction",
}

# Common OCR character confusions
OCR_CONFUSIONS = [
    ("0", "O"), ("O", "0"),
    ("1", "l"), ("l", "1"),
    ("1", "I"), ("I", "1"),
    ("5", "S"), ("S", "5"),
    ("8", "B"), ("B", "8"),
    ("2", "Z"), ("Z", "2"),
    ("6", "G"), ("G", "6"),
    ("0", "Q"), ("Q", "0"),
]


def infer_correction_category(
    field_path: str,
    extracted: str | None,
    corrected: str,
) -> str:
    """Auto-infer why a correction was made based on patterns.

    Args:
        field_path: The field being corrected (e.g., "invoice.rate_schedule")
        extracted: The originally extracted value
        corrected: The corrected value

    Returns:
        One of the CATEGORY_* constants
    """
    if extracted is None:
        return CATEGORY_MISSING_CONTEXT

    extracted = str(extracted).strip()
    corrected = str(corrected).strip()

    if not extracted or not corrected:
        return CATEGORY_OTHER

    # Check for year correction pattern in date fields
    if _is_date_field(field_path):
        if _is_year_correction(extracted, corrected):
            return CATEGORY_WRONG_ON_DOCUMENT

    # Check for trailing character removal ("1ENO" → "1E")
    if _is_trailing_removal(extracted, corrected):
        return CATEGORY_FORMAT_NORMALIZE

    # Check for leading character removal
    if _is_leading_removal(extracted, corrected):
        return CATEGORY_FORMAT_NORMALIZE

    # Check for whitespace/formatting normalization
    if _is_whitespace_normalization(extracted, corrected):
        return CATEGORY_FORMAT_NORMALIZE

    # Check for OCR character confusion
    if _is_ocr_confusion(extracted, corrected):
        return CATEGORY_OCR_ERROR

    # Check for numeric field calculation errors
    if _is_numeric_field(field_path) and _is_numeric_change(extracted, corrected):
        return CATEGORY_CALCULATION_ERROR

    return CATEGORY_OTHER


def _is_date_field(field_path: str) -> bool:
    """Check if field is a date field."""
    date_indicators = ["date", "period", "start", "end", "due", "billing"]
    return any(ind in field_path.lower() for ind in date_indicators)


def _is_numeric_field(field_path: str) -> bool:
    """Check if field is likely numeric."""
    numeric_indicators = ["amount", "total", "charge", "cost", "price", "quantity", "consumption", "reading"]
    return any(ind in field_path.lower() for ind in numeric_indicators)


def _is_year_correction(extracted: str, corrected: str) -> bool:
    """Check if correction is just a year change (e.g., 2023 → 2025)."""
    # Match date patterns like YYYY-MM-DD, DD/MM/YYYY, etc.
    date_pattern = r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})'

    ext_match = re.search(date_pattern, extracted)
    cor_match = re.search(date_pattern, corrected)

    if ext_match and cor_match:
        # Check if month and day are the same, only year differs
        ext_year, ext_month, ext_day = ext_match.groups()
        cor_year, cor_month, cor_day = cor_match.groups()

        if ext_month == cor_month and ext_day == cor_day and ext_year != cor_year:
            return True

    # Also check for short date formats like "21 AGO 23" → "21 AGO 25"
    short_pattern = r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{2})'
    ext_short = re.search(short_pattern, extracted)
    cor_short = re.search(short_pattern, corrected)

    if ext_short and cor_short:
        if (ext_short.group(1) == cor_short.group(1) and
            ext_short.group(2).lower() == cor_short.group(2).lower() and
            ext_short.group(3) != cor_short.group(3)):
            return True

    return False


def _is_trailing_removal(extracted: str, corrected: str) -> bool:
    """Check if correction removes trailing characters."""
    # Corrected is a prefix of extracted (e.g., "1ENO" → "1E")
    if extracted.startswith(corrected) and len(corrected) < len(extracted):
        return True
    # Case insensitive check
    if extracted.lower().startswith(corrected.lower()) and len(corrected) < len(extracted):
        return True
    return False


def _is_leading_removal(extracted: str, corrected: str) -> bool:
    """Check if correction removes leading characters."""
    if extracted.endswith(corrected) and len(corrected) < len(extracted):
        return True
    return False


def _is_whitespace_normalization(extracted: str, corrected: str) -> bool:
    """Check if correction is just whitespace/formatting."""
    # Remove all whitespace and compare
    ext_clean = re.sub(r'\s+', '', extracted)
    cor_clean = re.sub(r'\s+', '', corrected)

    if ext_clean == cor_clean:
        return True

    # Check for dash/hyphen normalization
    ext_norm = re.sub(r'[-–—]', '-', extracted)
    cor_norm = re.sub(r'[-–—]', '-', corrected)
    if ext_norm == cor_norm:
        return True

    return False


def _is_ocr_confusion(extracted: str, corrected: str) -> bool:
    """Check if the difference is likely an OCR character confusion."""
    if len(extracted) != len(corrected):
        return False

    # Count differences
    diffs = sum(1 for a, b in zip(extracted, corrected) if a != b)

    # If more than 2 character differences, probably not OCR
    if diffs > 2:
        return False

    # Check if all differences are known OCR confusions
    for i, (a, b) in enumerate(zip(extracted, corrected)):
        if a != b:
            if (a, b) not in OCR_CONFUSIONS and (b, a) not in OCR_CONFUSIONS:
                return False

    return diffs > 0


def _is_numeric_change(extracted: str, corrected: str) -> bool:
    """Check if both values are numeric."""
    try:
        # Clean currency symbols and commas
        ext_clean = re.sub(r'[$€£¥,\s]', '', extracted)
        cor_clean = re.sub(r'[$€£¥,\s]', '', corrected)
        float(ext_clean)
        float(cor_clean)
        return True
    except ValueError:
        return False


def get_category_description(category: str) -> str:
    """Get human-readable description for a category."""
    return CATEGORY_DESCRIPTIONS.get(category, "Unknown category")


def get_category_reasoning(category: str, field_path: str, extracted: str, corrected: str) -> str:
    """Generate a reasoning explanation for the few-shot context."""
    if category == CATEGORY_OCR_ERROR:
        return f"OCR commonly misreads characters in this field"
    elif category == CATEGORY_FORMAT_NORMALIZE:
        if _is_trailing_removal(extracted or "", corrected):
            return f"Remove trailing characters from {field_path.split('.')[-1]}"
        return f"Standardize format for {field_path.split('.')[-1]}"
    elif category == CATEGORY_WRONG_ON_DOCUMENT:
        if _is_date_field(field_path):
            return "Document contains incorrect year - verify against other date references"
        return "Document contains an error - cross-reference with other fields"
    elif category == CATEGORY_MISSING_CONTEXT:
        return "Additional context needed for correct interpretation"
    elif category == CATEGORY_CALCULATION_ERROR:
        return "Verify mathematical calculations"
    else:
        return "Review this field carefully"
