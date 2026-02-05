"""Build few-shot context from correction history."""
from __future__ import annotations
from .correction_store import CorrectionStore


def get_few_shot_context(
    store: CorrectionStore,
    utility: str | None = None,
    commodity: str | None = None,
    fingerprint: str | None = None,
    min_recurrence: int = 2,
    max_examples: int = 5,
) -> str:
    """Generate few-shot context from recurring corrections.

    Only includes patterns with >= min_recurrence occurrences (default 2).
    Returns formatted text for injection into prompts, or empty string.
    """
    patterns = store.group_by_pattern(utility=utility, commodity=commodity)

    # Filter by minimum recurrence
    qualifying = [p for p in patterns if p["count"] >= min_recurrence]

    if not qualifying:
        return ""

    # Limit to top patterns
    qualifying = qualifying[:max_examples]

    lines = ["## KNOWN ISSUES FOR THIS UTILITY/FORMAT", ""]
    lines.append("Based on previous corrections, watch for these known extraction issues:")
    lines.append("")

    for pattern in qualifying:
        lines.append(f"### Field: `{pattern['field_path']}` ({pattern['count']} occurrences)")
        for ex in pattern["examples"]:
            lines.append(f"  - Extracted: `{ex['extracted']}` -> Corrected: `{ex['corrected']}`")
            if ex.get("reason"):
                lines.append(f"    Reason: {ex['reason']}")
        lines.append("")

    return "\n".join(lines)
