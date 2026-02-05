"""Drift detection between extraction runs."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

# Field weight categories for drift severity
FATAL_FIELDS = {"total_amount_due", "account_number", "billing_period", "commodity_type", "meter_consumption"}
HIGH_FIELDS = {"current_charges", "demand_value", "rate_schedule", "section_subtotals"}


class DriftField(BaseModel):
    field_path: str
    old_value: str | None
    new_value: str | None
    severity: str  # fatal, high, medium, low


class DriftEvent(BaseModel):
    drift_fields: list[DriftField] = Field(default_factory=list)
    fatal_drift: bool = False
    cause_hypothesis: str | None = None


def detect_drift(new_extraction: dict, previous_extraction: dict) -> DriftEvent | None:
    """Compare two extractions of the same document and detect drift.

    Returns DriftEvent if differences found, None if identical.
    """
    diffs = _compare_dicts(new_extraction, previous_extraction, prefix="")

    if not diffs:
        return None

    drift_fields: list[DriftField] = []
    fatal = False

    for field_path, old_val, new_val in diffs:
        severity = _classify_drift_severity(field_path)
        if severity == "fatal":
            fatal = True
        drift_fields.append(DriftField(
            field_path=field_path,
            old_value=str(old_val) if old_val is not None else None,
            new_value=str(new_val) if new_val is not None else None,
            severity=severity,
        ))

    hypothesis = _hypothesize_cause(drift_fields, new_extraction, previous_extraction)

    return DriftEvent(drift_fields=drift_fields, fatal_drift=fatal, cause_hypothesis=hypothesis)


def _compare_dicts(new: dict, old: dict, prefix: str) -> list[tuple[str, Any, Any]]:
    """Recursively compare two dicts and return differences."""
    diffs: list[tuple[str, Any, Any]] = []

    # Skip metadata fields that change naturally
    skip_fields = {"extraction_id", "extraction_timestamp", "processing_time_ms", "few_shot_context_hash"}

    all_keys = set(list(new.keys()) + list(old.keys()))

    for key in all_keys:
        if key in skip_fields:
            continue

        path = f"{prefix}.{key}" if prefix else key
        new_val = new.get(key)
        old_val = old.get(key)

        if isinstance(new_val, dict) and isinstance(old_val, dict):
            diffs.extend(_compare_dicts(new_val, old_val, path))
        elif isinstance(new_val, list) and isinstance(old_val, list):
            if len(new_val) != len(old_val):
                diffs.append((path, f"len={len(old_val)}", f"len={len(new_val)}"))
            else:
                for i, (nv, ov) in enumerate(zip(new_val, old_val)):
                    if isinstance(nv, dict) and isinstance(ov, dict):
                        diffs.extend(_compare_dicts(nv, ov, f"{path}[{i}]"))
                    elif nv != ov:
                        diffs.append((f"{path}[{i}]", ov, nv))
        elif new_val != old_val:
            diffs.append((path, old_val, new_val))

    return diffs


def _classify_drift_severity(field_path: str) -> str:
    """Classify drift severity based on field path."""
    path_lower = field_path.lower()

    for fatal in FATAL_FIELDS:
        if fatal in path_lower:
            return "fatal"

    for high in HIGH_FIELDS:
        if high in path_lower:
            return "high"

    if any(kw in path_lower for kw in ("charge", "amount", "rate", "quantity")):
        return "medium"

    return "low"


def _hypothesize_cause(drift_fields: list[DriftField], new_ext: dict, old_ext: dict) -> str:
    """Try to determine why drift occurred."""
    new_meta = new_ext.get("extraction_metadata", {})
    old_meta = old_ext.get("extraction_metadata", {})

    # Check model version change
    new_models = new_meta.get("models_used", {})
    old_models = old_meta.get("models_used", {})
    if new_models != old_models:
        return "Model version change detected"

    # Check prompt version change
    new_prompts = new_meta.get("prompt_versions", {})
    old_prompts = old_meta.get("prompt_versions", {})
    if new_prompts != old_prompts:
        return "Prompt version change detected"

    # Check few-shot change
    new_fs = new_meta.get("few_shot_context_hash")
    old_fs = old_meta.get("few_shot_context_hash")
    if new_fs != old_fs:
        return "Few-shot context change detected"

    # Check if mostly low-severity
    severities = [f.severity for f in drift_fields]
    if all(s == "low" for s in severities):
        return "Minor output variation (LLM non-determinism)"

    return "Unknown cause -- manual investigation recommended"
