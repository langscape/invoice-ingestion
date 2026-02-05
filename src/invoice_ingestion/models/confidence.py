"""Confidence scoring and tier determination.

Implements the weighted, tiered scoring algorithm described in Section 5 of
the spec, plus the international adjustments from the addendum (Section 11).
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from invoice_ingestion.models.schema import ConfidenceTier, ComplexityTier

# ---------------------------------------------------------------------------
# Field weight configuration
# ---------------------------------------------------------------------------

FIELD_WEIGHTS: dict[str, dict[str, Any]] = {
    "fatal": {
        "fields": [
            "total_amount_due",
            "account_number",
            "billing_period",
            "commodity_type",
            "meter_consumption",
            "meter_multiplier",
        ],
        "error_penalty": 1.0,
    },
    "high": {
        "fields": [
            "current_charges",
            "demand_value",
            "rate_schedule",
            "section_subtotals",
            "tou_breakdown",
            "net_metering_values",
        ],
        "error_penalty": 0.20,
    },
    "medium": {
        "fields": [
            "individual_charge_amounts",
            "charge_classifications",
            "meter_read_dates",
            "supplier_name",
        ],
        "error_penalty": 0.08,
    },
    "low": {
        "fields": [
            "rider_descriptions",
            "billing_address",
            "late_fees",
            "previous_balance",
        ],
        "error_penalty": 0.03,
    },
}

# Pre-build a reverse lookup: field_name -> weight category.
_FIELD_TO_WEIGHT: dict[str, str] = {}
for _category, _info in FIELD_WEIGHTS.items():
    for _f in _info["fields"]:
        _FIELD_TO_WEIGHT[_f] = _category


def get_field_weight(field_path: str) -> str:
    """Return the weight category for *field_path*.

    The lookup first tries an exact match, then falls back to checking
    whether any known field name is a substring of *field_path*.  If nothing
    matches the field is classified as ``"low"``.
    """
    if field_path in _FIELD_TO_WEIGHT:
        return _FIELD_TO_WEIGHT[field_path]
    for known_field, category in _FIELD_TO_WEIGHT.items():
        if known_field in field_path:
            return category
    return "low"


# ---------------------------------------------------------------------------
# Helper: iterate per-field confidences
# ---------------------------------------------------------------------------


def iter_field_confidences(extraction: dict) -> list[tuple[str, float]]:
    """Walk the extraction dict and yield ``(field_path, confidence)`` pairs.

    Looks for any dict that has both ``"value"`` and ``"confidence"`` keys,
    treating them as ``ConfidentValue`` instances.
    """
    results: list[tuple[str, float]] = []

    def _walk(obj: Any, prefix: str) -> None:
        if isinstance(obj, dict):
            if "value" in obj and "confidence" in obj:
                results.append((prefix, obj["confidence"]))
            for key, val in obj.items():
                _walk(val, f"{prefix}.{key}" if prefix else key)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                _walk(item, f"{prefix}[{idx}]")

    _walk(extraction, "")
    return results


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class ConfidenceResult:
    """Outcome of the confidence scoring algorithm."""

    score: float
    fatal_triggered: bool
    tier: ConfidenceTier
    penalties: list[str] = dc_field(default_factory=list)


# ---------------------------------------------------------------------------
# Core scoring
# ---------------------------------------------------------------------------


def compute_confidence(
    extraction: dict,
    validation: dict,
    audit: dict,
) -> ConfidenceResult:
    """Compute the overall confidence score for an extraction.

    Parameters
    ----------
    extraction:
        The full extraction result as a dict (matching ``ExtractionResult``).
    validation:
        The ``validation`` sub-dict (``MathResults``, etc.).
    audit:
        The ``audit_results`` sub-dict from ``Validation``.

    Returns
    -------
    ConfidenceResult
        The numeric score, whether a fatal flag was tripped, and the tier.
    """

    score: float = 1.0
    fatal_triggered: bool = False
    penalties: list[str] = []

    # --- Math validation penalties ---
    math_results = validation.get("math_results", {})
    # Individual line-item dispositions are not directly in math_results in the
    # schema, but if callers attach a "line_dispositions" list we will honour it.
    for result in validation.get("line_dispositions", []):
        disposition = result.get("disposition", "")
        if disposition == "discrepancy":
            field = result.get("field", "unknown")
            weight = get_field_weight(field)
            penalty = FIELD_WEIGHTS[weight]["error_penalty"]
            score -= penalty
            penalties.append(f"math_discrepancy:{field}:-{penalty}")
            if weight == "fatal":
                fatal_triggered = True
        # Rounding and utility adjustments are NOT penalised.

    # --- Audit mismatches ---
    for mismatch in audit.get("mismatches", []):
        severity = mismatch.get("severity", "low")
        penalty = FIELD_WEIGHTS.get(severity, FIELD_WEIGHTS["low"])["error_penalty"]
        score -= penalty
        field = mismatch.get("field", "unknown")
        penalties.append(f"audit_mismatch:{field}:-{penalty}")
        if severity == "fatal":
            fatal_triggered = True

    # --- Low per-field confidence ---
    for field_path, confidence in iter_field_confidences(extraction):
        if confidence < 0.80:
            weight = get_field_weight(field_path)
            if weight == "fatal":
                fatal_triggered = True
                score -= 0.15
                penalties.append(f"low_conf_fatal:{field_path}:-0.15")
            elif weight == "high":
                score -= 0.10
                penalties.append(f"low_conf_high:{field_path}:-0.10")
            elif weight == "medium":
                score -= 0.04
                penalties.append(f"low_conf_medium:{field_path}:-0.04")
            # low weight fields: no additional penalty

    # --- Image quality ---
    source_doc = extraction.get("extraction_metadata", {}).get("source_document", {})
    quality = source_doc.get("image_quality_score", 1.0)
    if quality < 0.6:
        score -= 0.10
        penalties.append(f"low_image_quality:{quality}:-0.10")

    # --- OCR penalty ---
    if source_doc.get("ocr_applied", False):
        score -= 0.03
        penalties.append("ocr_applied:-0.03")

    score = max(score, 0.0)

    complexity_raw = extraction.get("classification", {}).get(
        "complexity_tier", "simple"
    )
    try:
        complexity = ComplexityTier(complexity_raw)
    except ValueError:
        complexity = ComplexityTier.SIMPLE

    tier = determine_tier(score, fatal_triggered, complexity)

    return ConfidenceResult(
        score=round(score, 4),
        fatal_triggered=fatal_triggered,
        tier=tier,
        penalties=penalties,
    )


# ---------------------------------------------------------------------------
# Tier determination
# ---------------------------------------------------------------------------


def determine_tier(
    score: float,
    fatal_triggered: bool,
    complexity: ComplexityTier,
) -> ConfidenceTier:
    """Map a numeric confidence score to a review tier.

    Parameters
    ----------
    score:
        Numeric confidence in ``[0, 1]``.
    fatal_triggered:
        Whether any fatal-weight field had an error.
    complexity:
        The invoice complexity tier (affects threshold choice).
    """

    if fatal_triggered:
        return ConfidenceTier.FULL_REVIEW

    if complexity in (ComplexityTier.COMPLEX, ComplexityTier.PATHOLOGICAL):
        if score >= 0.90:
            return ConfidenceTier.AUTO_ACCEPT
        if score >= 0.75:
            return ConfidenceTier.TARGETED_REVIEW
        return ConfidenceTier.FULL_REVIEW

    # simple / standard
    if score >= 0.95:
        return ConfidenceTier.AUTO_ACCEPT
    if score >= 0.82:
        return ConfidenceTier.TARGETED_REVIEW
    return ConfidenceTier.FULL_REVIEW


# ---------------------------------------------------------------------------
# International confidence adjustments
# ---------------------------------------------------------------------------


def _count_ambiguous_dates(extraction: dict) -> int:
    """Count date fields flagged as ambiguous."""
    count = 0
    billing = extraction.get("invoice", {}).get("billing_period", {})
    for key in ("start", "end"):
        if billing.get(key, {}).get("ambiguous", False):
            count += 1
    return count


def compute_confidence_international(
    extraction: dict,
    validation: dict,
    audit: dict,
    locale: dict,
) -> ConfidenceResult:
    """Compute confidence with international adjustments layered on top.

    Extends :func:`compute_confidence` with penalties for:
    - Uncertain number-format detection
    - Ambiguous dates
    - VAT validation failures
    - Calorific conversion mismatches
    - Uncommon languages

    And a bonus for structured invoice data (Factur-X / ZUGFeRD).
    """

    base = compute_confidence(extraction, validation, audit)
    score = base.score
    penalties = list(base.penalties)
    fatal_triggered = base.fatal_triggered

    # Number-format confidence
    nf_confidence = locale.get("number_format_confidence", 1.0)
    if nf_confidence < 0.7:
        score -= 0.10
        penalties.append(f"number_format_uncertain:{nf_confidence}:-0.10")

    # Ambiguous dates
    ambiguous = _count_ambiguous_dates(extraction)
    if ambiguous > 0:
        penalty = 0.05 * ambiguous
        score -= penalty
        penalties.append(f"ambiguous_dates:{ambiguous}:-{penalty}")

    # VAT validation errors (excluding rounding)
    for err in validation.get("vat_errors", []):
        if not err.get("is_rounding", False):
            score -= 0.12
            penalties.append(f"vat_error:{err.get('field', '?')}:-0.12")

    # Calorific conversion errors
    for err in validation.get("conversion_errors", []):
        score -= 0.15
        penalties.append(f"conversion_error:{err.get('field', '?')}:-0.15")

    # Uncommon language
    language = locale.get("language", "en")
    if language not in ("en", "de", "fr", "es", "it", "nl", "pt"):
        score -= 0.05
        penalties.append(f"uncommon_language:{language}:-0.05")

    # Structured invoice bonus
    classification = extraction.get("classification", {})
    if classification.get("has_structured_invoice_data", False):
        score += 0.10
        penalties.append("structured_invoice_bonus:+0.10")

    score = max(score, 0.0)

    complexity_raw = classification.get("complexity_tier", "simple")
    try:
        complexity = ComplexityTier(complexity_raw)
    except ValueError:
        complexity = ComplexityTier.SIMPLE

    tier = determine_tier(score, fatal_triggered, complexity)

    return ConfidenceResult(
        score=round(score, 4),
        fatal_triggered=fatal_triggered,
        tier=tier,
        penalties=penalties,
    )
