"""Locale-aware date parsing for energy invoices."""
from __future__ import annotations
from datetime import date
import re

# Common date patterns
DATE_PATTERNS = [
    # ISO
    (r'(\d{4})-(\d{2})-(\d{2})', 'YYYY-MM-DD', lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    # European with dots
    (r'(\d{2})\.(\d{2})\.(\d{4})', 'DD.MM.YYYY', lambda m: (int(m[3]), int(m[2]), int(m[1]))),
    # Slash format (ambiguous)
    (r'(\d{2})/(\d{2})/(\d{4})', 'DD/MM/YYYY or MM/DD/YYYY', None),
    # Dash format (ambiguous)
    (r'(\d{2})-(\d{2})-(\d{4})', 'DD-MM-YYYY or MM-DD-YYYY', None),
]

def detect_date_format(text: str) -> str:
    """Detect predominant date format from text.
    Returns format string like 'DD/MM/YYYY' or 'MM/DD/YYYY' or 'DD.MM.YYYY'.
    """
    # Check for unambiguous European dot format
    dot_dates = re.findall(r'\d{2}\.\d{2}\.\d{4}', text)
    if dot_dates:
        return "DD.MM.YYYY"

    # Check for ISO
    iso_dates = re.findall(r'\d{4}-\d{2}-\d{2}', text)
    if iso_dates:
        return "YYYY-MM-DD"

    # Check slash dates and try to disambiguate
    slash_dates = re.findall(r'(\d{2})/(\d{2})/(\d{4})', text)
    if slash_dates:
        for d1, d2, _ in slash_dates:
            d1_int, d2_int = int(d1), int(d2)
            if d1_int > 12:
                return "DD/MM/YYYY"
            if d2_int > 12:
                return "MM/DD/YYYY"

    return "MM/DD/YYYY"  # Default US


def parse_date(raw_string: str, date_format: str = "MM/DD/YYYY") -> date:
    """Parse date string to date object using the given format."""
    s = raw_string.strip()

    # ISO format
    iso_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', s)
    if iso_match:
        return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))

    # Dot format (European)
    dot_match = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', s)
    if dot_match:
        day, month, year = int(dot_match.group(1)), int(dot_match.group(2)), int(dot_match.group(3))
        return date(year, month, day)

    # Slash or dash format
    sep_match = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', s)
    if sep_match:
        p1, p2, year = int(sep_match.group(1)), int(sep_match.group(2)), int(sep_match.group(3))
        if date_format.startswith("DD"):
            day, month = p1, p2
        else:
            month, day = p1, p2
        return date(year, month, day)

    raise ValueError(f"Cannot parse date: {raw_string} with format {date_format}")


def is_date_ambiguous(date_string: str) -> bool:
    """Check if a date string is ambiguous (both DD/MM and MM/DD interpretations are valid)."""
    s = date_string.strip()
    sep_match = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$', s)
    if not sep_match:
        return False

    p1, p2 = int(sep_match.group(1)), int(sep_match.group(2))
    # Ambiguous if both parts could be valid month values (1-12)
    return 1 <= p1 <= 12 and 1 <= p2 <= 12 and p1 != p2


def validate_billing_period(start: date, end: date) -> tuple[bool, str | None]:
    """Validate billing period sanity. Returns (is_valid, error_message)."""
    days = (end - start).days
    if days < 0:
        return False, f"Billing period is negative: {days} days (start={start}, end={end})"
    if days == 0:
        return False, "Billing period is zero days"
    if days > 400:
        return False, f"Billing period exceeds 400 days: {days} days"
    if days < 15:
        return True, f"Unusually short billing period: {days} days"
    if days > 95:
        return True, f"Unusually long billing period: {days} days"
    return True, None
