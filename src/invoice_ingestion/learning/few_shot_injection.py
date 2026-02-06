"""Build few-shot context from correction history."""
from __future__ import annotations
from .correction_store import CorrectionStore
from .correction_inference import get_category_reasoning, CATEGORY_DESCRIPTIONS


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
    lines.append("Based on previous human corrections, watch for these known extraction issues:")
    lines.append("")

    for pattern in qualifying:
        field_path = pattern["field_path"]
        category = pattern.get("category")
        count = pattern["count"]

        # Build header with category if available
        if category and category in CATEGORY_DESCRIPTIONS:
            category_desc = CATEGORY_DESCRIPTIONS[category]
            lines.append(f"### Field: `{field_path}` ({count} corrections) - {category_desc}")
        else:
            lines.append(f"### Field: `{field_path}` ({count} corrections)")

        # Add reasoning based on category
        examples = pattern["examples"]
        if examples and category:
            reasoning = get_category_reasoning(
                category,
                field_path,
                examples[0].get("extracted", ""),
                examples[0].get("corrected", ""),
            )
            lines.append(f"**Why:** {reasoning}")
            lines.append("")

        # Add examples
        lines.append("**Examples:**")
        for ex in examples:
            lines.append(f"  - `{ex['extracted']}` -> `{ex['corrected']}`")
            if ex.get("reason"):
                lines.append(f"    (Note: {ex['reason']})")
        lines.append("")

    return "\n".join(lines)
