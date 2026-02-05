"""VAT validation for European invoices."""
from __future__ import annotations

class VATValidationResult:
    def __init__(self):
        self.issues: list[dict] = []
        self.passed: bool = True

    def add_issue(self, severity: str, rule: str, message: str, expected: float | None = None, actual: float | None = None):
        self.issues.append({
            "severity": severity,
            "rule": rule,
            "message": message,
            "expected": expected,
            "actual": actual,
        })
        if severity == "error":
            self.passed = False


def validate_vat(extraction: dict, tolerance: float = 0.05) -> VATValidationResult:
    """Validate VAT calculations on an extraction.

    4 rules from addendum Section 6.1:
    1. For each charge with vat_rate and amount_net: amount_net × vat_rate ≈ vat_amount
    2. For each charge: amount_net + vat_amount ≈ amount_gross
    3. VAT summary: sum of line-level vat by rate ≈ summary vat by rate
    4. Totals: total_net + total_vat ≈ total_gross
    """
    result = VATValidationResult()
    totals = extraction.get("totals", {})
    charges = extraction.get("charges", [])

    # Rule 1 & 2: Line-level VAT
    vat_by_rate: dict[float, dict] = {}

    for charge in charges:
        amount_net = _get_value(charge.get("amount_net"))
        vat_rate = charge.get("vat_rate")
        vat_amount = _get_value(charge.get("vat_amount"))
        amount_gross = _get_value(charge.get("amount_gross"))
        vat_category = charge.get("vat_category")

        if amount_net is not None and vat_rate is not None and vat_amount is not None:
            # Rule 1: net × rate ≈ vat_amount
            # Skip reverse charge
            if vat_category == "reverse_charge":
                if vat_amount != 0:
                    result.add_issue("warning", "vat_reverse_charge",
                                    f"Reverse charge but VAT amount is {vat_amount}, expected 0",
                                    expected=0, actual=vat_amount)
            else:
                expected_vat = round(amount_net * vat_rate, 2)
                if abs(expected_vat - vat_amount) > tolerance:
                    result.add_issue("error", "vat_line_calculation",
                                    f"Line VAT mismatch: {amount_net} × {vat_rate} = {expected_vat}, stated {vat_amount}",
                                    expected=expected_vat, actual=vat_amount)

            # Accumulate for summary check
            if vat_rate not in vat_by_rate:
                vat_by_rate[vat_rate] = {"taxable_base": 0.0, "vat_amount": 0.0}
            vat_by_rate[vat_rate]["taxable_base"] += amount_net
            vat_by_rate[vat_rate]["vat_amount"] += vat_amount

        # Rule 2: net + vat ≈ gross
        if amount_net is not None and vat_amount is not None and amount_gross is not None:
            expected_gross = round(amount_net + vat_amount, 2)
            if abs(expected_gross - amount_gross) > tolerance:
                result.add_issue("error", "vat_net_plus_vat",
                                f"Net + VAT mismatch: {amount_net} + {vat_amount} = {expected_gross}, stated gross {amount_gross}",
                                expected=expected_gross, actual=amount_gross)

    # Rule 3: VAT summary crosscheck
    vat_summary = totals.get("vat_summary", [])
    if vat_summary and vat_by_rate:
        for summary_entry in vat_summary:
            rate = summary_entry.get("vat_rate")
            summary_base = _get_value(summary_entry.get("taxable_base"))
            summary_vat = _get_value(summary_entry.get("vat_amount"))

            if rate in vat_by_rate and summary_base is not None:
                line_base = round(vat_by_rate[rate]["taxable_base"], 2)
                if abs(line_base - summary_base) > tolerance * 2:
                    result.add_issue("warning", "vat_summary_base",
                                    f"VAT summary base for rate {rate}: lines sum to {line_base}, summary says {summary_base}",
                                    expected=line_base, actual=summary_base)

            if rate in vat_by_rate and summary_vat is not None:
                line_vat = round(vat_by_rate[rate]["vat_amount"], 2)
                if abs(line_vat - summary_vat) > tolerance * 2:
                    result.add_issue("warning", "vat_summary_amount",
                                    f"VAT summary amount for rate {rate}: lines sum to {line_vat}, summary says {summary_vat}",
                                    expected=line_vat, actual=summary_vat)

    # Rule 4: total_net + total_vat ≈ total_gross
    total_net = _get_value(totals.get("total_net"))
    total_vat = _get_value(totals.get("total_vat"))
    total_gross = _get_value(totals.get("total_gross"))

    if total_net is not None and total_vat is not None and total_gross is not None:
        expected_total = round(total_net + total_vat, 2)
        if abs(expected_total - total_gross) > tolerance:
            result.add_issue("error", "vat_total",
                            f"Total net + total VAT mismatch: {total_net} + {total_vat} = {expected_total}, stated gross {total_gross}",
                            expected=expected_total, actual=total_gross)

    return result


def _get_value(field) -> float | None:
    """Extract numeric value from a field that could be a dict with 'value' key or a plain number."""
    if field is None:
        return None
    if isinstance(field, (int, float)):
        return float(field)
    if isinstance(field, dict):
        return field.get("value")
    return None
