"""Locale-aware number parsing for energy invoices."""
from __future__ import annotations
import re

def detect_number_format(text: str) -> str:
    """Detect number format from text samples.
    Returns format string like '1.234,56' (EU) or '1,234.56' (US).

    Algorithm:
    - Find all number-like patterns in text
    - If last separator is comma and has 2 digits after: EU format (1.234,56)
    - If last separator is period and has 2 digits after: US format (1,234.56)
    - Count occurrences of each pattern for confidence
    """
    # Find patterns like: 1.234,56 or 1,234.56 or 1234,56 or 1234.56
    eu_pattern = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}\b', text)
    us_pattern = re.findall(r'\d{1,3}(?:,\d{3})*\.\d{2}\b', text)

    if len(eu_pattern) > len(us_pattern):
        return "1.234,56"
    elif len(us_pattern) > len(eu_pattern):
        return "1,234.56"

    # Fallback: check for single-separator patterns
    eu_single = re.findall(r'\d+,\d{2}\b', text)
    us_single = re.findall(r'\d+\.\d{2}\b', text)

    if len(eu_single) > len(us_single):
        return "1.234,56"
    return "1,234.56"  # default US


def parse_amount(raw_string: str, number_format: str = "1,234.56") -> float:
    """Parse a monetary amount string to float.

    Handles:
    - EU format: "1.234,56" → 1234.56
    - US format: "1,234.56" → 1234.56
    - Plain: "1234.56" or "1234,56" → 1234.56
    - Currency symbols: "€ 1.234,56", "$1,234.56", "1.234,56 €"
    - Negative: "(23,66)", "23.66-", "-23.66", "- 23,66"
    - Spaces as thousands separator: "1 234,56"
    """
    if not raw_string or not raw_string.strip():
        raise ValueError(f"Empty amount string")

    cleaned = raw_string.strip()

    # Detect negative
    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative = True
        cleaned = cleaned[1:-1].strip()
    elif cleaned.startswith("-") or cleaned.startswith("- "):
        negative = True
        cleaned = cleaned.lstrip("- ")
    elif cleaned.endswith("-"):
        negative = True
        cleaned = cleaned[:-1].strip()

    # Strip currency symbols and whitespace
    cleaned = re.sub(r'[€$£¥₹₽R\s]', '', cleaned)
    cleaned = re.sub(r'[A-Z]{3}\s*', '', cleaned)  # Strip ISO currency codes like EUR, USD

    if not cleaned:
        raise ValueError(f"No numeric content in: {raw_string}")

    if number_format == "1.234,56":
        # EU: dots are thousands, comma is decimal
        cleaned = cleaned.replace('.', '')
        cleaned = cleaned.replace(',', '.')
    else:
        # US: commas are thousands, dot is decimal
        cleaned = cleaned.replace(',', '')

    result = float(cleaned)
    return -result if negative else result


def strip_currency(raw_string: str) -> tuple[str, str | None]:
    """Strip currency symbol/code from amount string. Returns (amount_str, currency_code)."""
    s = raw_string.strip()

    currency_map = {
        '€': 'EUR', '$': 'USD', '£': 'GBP', '¥': 'JPY', '₹': 'INR',
        '₽': 'RUB', 'R$': 'BRL', 'CHF': 'CHF',
    }

    for symbol, code in currency_map.items():
        if s.startswith(symbol):
            return s[len(symbol):].strip(), code
        if s.endswith(symbol):
            return s[:-len(symbol)].strip(), code

    # Check for ISO codes
    iso_match = re.match(r'^([A-Z]{3})\s+(.+)$', s)
    if iso_match:
        return iso_match.group(2), iso_match.group(1)
    iso_match = re.match(r'^(.+?)\s+([A-Z]{3})$', s)
    if iso_match:
        return iso_match.group(1), iso_match.group(2)

    return s, None
