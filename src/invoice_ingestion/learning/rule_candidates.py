"""Detect candidate validation rules from correction patterns."""
from __future__ import annotations
from .correction_store import CorrectionStore


def detect_rule_candidates(store: CorrectionStore, min_occurrences: int = 5) -> list[dict]:
    """Analyze correction patterns and suggest new validation rules.

    A pattern becomes a rule candidate when:
    - Same field_path has been corrected >= min_occurrences times
    - The corrections follow a consistent pattern (same direction/type)
    """
    patterns = store.group_by_pattern()

    candidates: list[dict] = []
    for pattern in patterns:
        if pattern["count"] < min_occurrences:
            continue

        examples = pattern["examples"]

        # Analyze consistency
        candidate = {
            "field_path": pattern["field_path"],
            "occurrence_count": pattern["count"],
            "examples": examples,
            "suggested_rule": _suggest_rule(pattern["field_path"], examples),
        }
        candidates.append(candidate)

    return candidates


def _suggest_rule(field_path: str, examples: list[dict]) -> str:
    """Suggest a validation rule based on correction examples."""
    if not examples:
        return "Unknown pattern"

    # Check if all corrections are numeric adjustments
    numeric_adjustments: list[float] = []
    for ex in examples:
        try:
            extracted = float(ex["extracted"])
            corrected = float(ex["corrected"])
            numeric_adjustments.append(corrected - extracted)
        except (ValueError, TypeError):
            pass

    if len(numeric_adjustments) == len(examples) and numeric_adjustments:
        avg_adj = sum(numeric_adjustments) / len(numeric_adjustments)
        if all(adj > 0 for adj in numeric_adjustments):
            return f"Values consistently under-extracted by ~{abs(avg_adj):.2f}. Consider adding rounding adjustment."
        elif all(adj < 0 for adj in numeric_adjustments):
            return f"Values consistently over-extracted by ~{abs(avg_adj):.2f}. Check for included tax/surcharge."

    # Check if it's a classification error
    if "category" in field_path or "section" in field_path:
        return f"Classification inconsistency on {field_path}. Consider adding a mapping rule."

    return f"Recurring correction on {field_path}. Review extraction logic."
