"""Locale-aware data types and settings for international invoice parsing.

Provides lightweight models for number/date formatting and a ``LocaleSettings``
container that downstream passes use to interpret raw strings correctly.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class NumberFormat(BaseModel):
    """Describes the number formatting convention used on an invoice."""

    decimal_separator: str = "."
    thousands_separator: str = ","
    example: str = "1,234.56"


class ParsedAmount(BaseModel):
    """Result of parsing a monetary string into a canonical float."""

    value: float
    original_string: str
    currency: str | None = None


class ParsedDate(BaseModel):
    """Result of parsing a date string with format tracking."""

    value: date
    original_string: str
    format_used: str
    ambiguous: bool = False


class LocaleSettings(BaseModel):
    """Locale configuration for a single invoice.

    Populated during Pass 0 based on language detection, currency symbols,
    number-format heuristics, and (optionally) explicit country signals.
    """

    country_code: str | None = None
    language: str = "en"
    currency_code: str = "USD"
    number_format: NumberFormat = Field(default_factory=NumberFormat)
    date_format: str = "MM/DD/YYYY"
