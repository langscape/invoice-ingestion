"""Complexity classification logic for invoice routing.

Derives a ``ComplexityTier`` from structural signals detected during
Pass 0.5.  The scoring mirrors the spec (Section 4, Pass 0.5) plus the
EU addendum additions.
"""

from __future__ import annotations

from invoice_ingestion.models.schema import ComplexityTier

# Signals whose presence adds +3 to the complexity score.
HIGH_COMPLEXITY_SIGNALS: frozenset[str] = frozenset(
    {
        "multi_meter",
        "net_metering",
        "prior_period_adjustments",
        "multi_page_charges",
    }
)

# Signals whose presence adds +1 to the complexity score.
MEDIUM_COMPLEXITY_SIGNALS: frozenset[str] = frozenset(
    {
        "tou_present",
        "demand_charges",
        "supplier_split",
        "tiered_rates",
    }
)


def classify_complexity(
    signals: list[str],
    line_item_count: int,
    page_count: int,
    has_multiple_vat_rates: bool = False,
    has_calorific_conversion: bool = False,
    has_contracted_capacity: bool = False,
) -> ComplexityTier:
    """Compute the complexity tier for an invoice.

    Scoring rules
    -------------
    * Each signal in ``HIGH_COMPLEXITY_SIGNALS`` adds **+3**.
    * Each signal in ``MEDIUM_COMPLEXITY_SIGNALS`` adds **+1**.
    * EU additions from the international addendum:
      - ``has_multiple_vat_rates`` adds **+2**.
      - ``has_calorific_conversion`` adds **+2**.
      - ``has_contracted_capacity`` adds **+1**.
    * Line-item count above 30 adds **+3**; above 15 adds **+1**.
    * Page count above 5 adds **+2**.

    Tier thresholds
    ---------------
    * ``<= 2`` -- simple
    * ``<= 6`` -- standard
    * ``<= 10`` -- complex
    * ``> 10`` -- pathological
    """

    score: int = 0

    # --- Signal scoring ---
    for signal in signals:
        if signal in HIGH_COMPLEXITY_SIGNALS:
            score += 3
        elif signal in MEDIUM_COMPLEXITY_SIGNALS:
            score += 1

    # --- EU / international additions ---
    if has_multiple_vat_rates:
        score += 2
    if has_calorific_conversion:
        score += 2
    if has_contracted_capacity:
        score += 1

    # --- Line-item count ---
    if line_item_count > 30:
        score += 3
    elif line_item_count > 15:
        score += 1

    # --- Page count ---
    if page_count > 5:
        score += 2

    # --- Derive tier ---
    if score <= 2:
        return ComplexityTier.SIMPLE
    if score <= 6:
        return ComplexityTier.STANDARD
    if score <= 10:
        return ComplexityTier.COMPLEX
    return ComplexityTier.PATHOLOGICAL
