"""Rounding rules per jurisdiction."""
from __future__ import annotations

ROUNDING_RULES: dict[str, dict] = {
    "DE": {"base_tolerance": 0.02, "tax_tolerance": 0.04, "note": "German rounding: base 2 cent, tax 4 cent"},
    "FR": {"base_tolerance": 0.05, "tax_tolerance": 0.10, "note": "French rounding: base 5 cent, tax 10 cent"},
    "ES": {"base_tolerance": 0.02, "tax_tolerance": 0.04, "note": "Spanish rounding"},
    "UK": {"base_tolerance": 0.01, "tax_tolerance": 0.02, "note": "UK: penny rounding"},
    "GB": {"base_tolerance": 0.01, "tax_tolerance": 0.02, "note": "UK: penny rounding"},
    "IT": {"base_tolerance": 0.02, "tax_tolerance": 0.04, "note": "Italian rounding"},
    "NL": {"base_tolerance": 0.02, "tax_tolerance": 0.04, "note": "Dutch rounding"},
    "US": {"base_tolerance": 0.05, "tax_tolerance": 0.05, "note": "US: nickel tolerance"},
    "MX": {"base_tolerance": 0.05, "tax_tolerance": 0.05, "note": "Mexico: 5 centavo tolerance"},
}

DEFAULT_RULES = {"base_tolerance": 0.05, "tax_tolerance": 0.10}


def get_rounding_tolerance(country_code: str | None, is_tax: bool = False) -> float:
    """Get rounding tolerance for a jurisdiction."""
    rules = ROUNDING_RULES.get(country_code or "US", DEFAULT_RULES)
    return rules["tax_tolerance"] if is_tax else rules["base_tolerance"]


def is_within_tolerance(expected: float, actual: float, country_code: str | None = None, is_tax: bool = False) -> bool:
    """Check if variance is within acceptable rounding tolerance."""
    tolerance = get_rounding_tolerance(country_code, is_tax)
    return abs(expected - actual) <= tolerance
