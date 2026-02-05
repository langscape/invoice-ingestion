"""Pass 3: Deterministic Validation -- pure code + optional LLM repair."""
from __future__ import annotations
import structlog
from ..models.internal import Pass3Result, ValidationIssue
from ..models.schema import MathDisposition
from ..international.rounding_rules import get_rounding_tolerance, is_within_tolerance
from ..international.vat import validate_vat
from ..international.gas_conversion import validate_gas_conversion

logger = structlog.get_logger(__name__)


def validate_line_item_math(charge: dict, country_code: str | None = None) -> ValidationIssue | None:
    """Validate: quantity x rate ~ amount."""
    qty = charge.get("quantity", {}).get("value") if isinstance(charge.get("quantity"), dict) else None
    rate = charge.get("rate", {}).get("value") if isinstance(charge.get("rate"), dict) else None
    amount = charge.get("amount", {}).get("value") if isinstance(charge.get("amount"), dict) else charge.get("amount")

    if qty is None or rate is None or amount is None:
        return None

    expected = round(qty * rate, 2)
    variance = abs(expected - amount)
    tolerance = get_rounding_tolerance(country_code)

    if variance == 0:
        return None  # Clean
    elif variance <= tolerance:
        return None  # Within rounding tolerance
    elif amount > expected and charge.get("category") == "fixed":
        return ValidationIssue(
            field=f"charges.{charge.get('line_id', '?')}.amount",
            severity="info",
            message=f"Possible minimum bill: expected {expected}, stated {amount}",
            expected=str(expected),
            actual=str(amount),
        )
    elif variance <= amount * 0.02:
        return ValidationIssue(
            field=f"charges.{charge.get('line_id', '?')}.amount",
            severity="info",
            message=f"Small variance (utility adjustment?): expected {expected}, stated {amount}",
            expected=str(expected),
            actual=str(amount),
        )
    else:
        return ValidationIssue(
            field=f"charges.{charge.get('line_id', '?')}.amount",
            severity="warning",
            message=f"Math discrepancy: {qty} x {rate} = {expected}, stated {amount}",
            expected=str(expected),
            actual=str(amount),
        )


def validate_totals(extraction: dict, country_code: str | None = None) -> list[ValidationIssue]:
    """Validate line items sum to stated totals."""
    issues: list[ValidationIssue] = []
    charges = extraction.get("charges", [])
    totals = extraction.get("totals", {})
    tolerance = get_rounding_tolerance(country_code) * 2  # wider for totals

    # Sum by section
    for section in ["supply", "distribution", "taxes", "other"]:
        section_charges = [c for c in charges if c.get("charge_section") == section]
        if not section_charges:
            continue
        calculated = sum(_get_amount(c) for c in section_charges if _get_amount(c) is not None)
        stated_key = f"{section}_subtotal"
        stated = _get_amount(totals.get(stated_key))
        if stated is not None:
            variance = abs(calculated - stated)
            if variance > tolerance:
                issues.append(ValidationIssue(
                    field=f"totals.{stated_key}",
                    severity="warning",
                    message=f"Section sum mismatch: calculated {calculated:.2f}, stated {stated:.2f}",
                    expected=str(round(calculated, 2)),
                    actual=str(stated),
                ))

    # Total current charges
    all_sum = sum(_get_amount(c) for c in charges if _get_amount(c) is not None)
    stated_total = _get_amount(totals.get("current_charges"))
    if stated_total is not None:
        variance = abs(all_sum - stated_total)
        if variance > tolerance * 2:
            min_bill = totals.get("minimum_bill_applied", False)
            if min_bill:
                issues.append(ValidationIssue(
                    field="totals.current_charges",
                    severity="info",
                    message=f"Minimum bill detected: calculated {all_sum:.2f}, stated {stated_total:.2f}",
                ))
            else:
                issues.append(ValidationIssue(
                    field="totals.current_charges",
                    severity="warning",
                    message=f"Total mismatch: sum of charges {all_sum:.2f}, stated {stated_total:.2f}",
                    expected=str(round(all_sum, 2)),
                    actual=str(stated_total),
                ))

    return issues


def validate_meters(extraction: dict) -> list[ValidationIssue]:
    """Validate meter reads -> consumption."""
    issues: list[ValidationIssue] = []
    for i, meter in enumerate(extraction.get("meters", [])):
        prev = meter.get("previous_read")
        curr = meter.get("current_read")
        if prev is not None and curr is not None:
            multiplier = 1.0
            if isinstance(meter.get("multiplier"), dict):
                multiplier = meter["multiplier"].get("value", 1.0)
            elif isinstance(meter.get("multiplier"), (int, float)):
                multiplier = meter["multiplier"]

            calc = (curr - prev) * multiplier
            consumption = meter.get("consumption", {})
            stated = consumption.get("raw_value") if isinstance(consumption, dict) else consumption
            if stated is not None and abs(calc - stated) > 1:
                meter_id = meter.get("meter_number", {}).get("value", f"meter_{i}") if isinstance(meter.get("meter_number"), dict) else f"meter_{i}"
                issues.append(ValidationIssue(
                    field=f"meters.{meter_id}.consumption",
                    severity="warning",
                    message=f"Read diff: ({curr}-{prev})x{multiplier}={calc}, stated={stated}",
                    expected=str(calc),
                    actual=str(stated),
                ))

        # TOU sums
        tou = meter.get("tou_breakdown")
        if tou:
            tou_sum = sum(t.get("consumption", {}).get("value", 0) for t in tou)
            total = meter.get("consumption", {}).get("raw_value")
            if total is not None and abs(tou_sum - total) > 1:
                issues.append(ValidationIssue(
                    field=f"meters.{i}.tou",
                    severity="warning",
                    message=f"TOU sum ({tou_sum}) != total consumption ({total})",
                ))

    return issues


def validate_logic(extraction: dict) -> list[ValidationIssue]:
    """Logic validation checks."""
    issues: list[ValidationIssue] = []
    classification = extraction.get("classification", {})
    commodity = classification.get("commodity_type", "")

    # Commodity-unit consistency
    for meter in extraction.get("meters", []):
        unit = meter.get("consumption", {}).get("raw_unit", "") if isinstance(meter.get("consumption"), dict) else ""
        if commodity == "electricity" and unit.lower() in ("therms", "ccf", "mcf", "dekatherms"):
            issues.append(ValidationIssue(
                field="meters.consumption.raw_unit",
                severity="fatal",
                message="Gas units on electricity invoice",
            ))
        if commodity == "natural_gas" and unit.lower() in ("kwh", "kw") and extraction.get("extraction_metadata", {}).get("locale_context", {}).get("country_code") in (None, "US"):
            issues.append(ValidationIssue(
                field="meters.consumption.raw_unit",
                severity="fatal",
                message="Electric units on US gas invoice",
            ))

    # Billing period
    invoice = extraction.get("invoice", {})
    bp = invoice.get("billing_period", {})
    days = bp.get("days")
    if days is not None:
        if days > 95 or days < 15:
            issues.append(ValidationIssue(
                field="invoice.billing_period.days",
                severity="warning",
                message=f"Unusual billing period: {days} days",
            ))

    # Negative amounts on non-credits
    for charge in extraction.get("charges", []):
        amount = _get_amount(charge)
        if amount is not None and amount < 0 and charge.get("category") not in ("credit", "adjustment"):
            desc = charge.get("description", {}).get("value", "?") if isinstance(charge.get("description"), dict) else "?"
            issues.append(ValidationIssue(
                field=f"charges.{charge.get('line_id', '?')}",
                severity="warning",
                message=f"Negative amount on non-credit line: {desc}",
            ))

    # Demand expected but missing
    if classification.get("has_demand_charges"):
        has_demand = any(c.get("category") == "demand" for c in extraction.get("charges", []))
        if not has_demand:
            issues.append(ValidationIssue(
                field="charges",
                severity="warning",
                message="Classification detected demand charges but none found",
            ))

    # TOU expected but missing
    if classification.get("has_tou"):
        has_tou = any(m.get("tou_breakdown") for m in extraction.get("meters", []))
        if not has_tou:
            issues.append(ValidationIssue(
                field="meters.tou_breakdown",
                severity="warning",
                message="Classification detected TOU but no TOU breakdown found",
            ))

    # Supplier split expected but all same owner
    if classification.get("has_supplier_split"):
        owners = set(c.get("charge_owner") for c in extraction.get("charges", []))
        if len(owners) <= 1:
            issues.append(ValidationIssue(
                field="charges.charge_owner",
                severity="warning",
                message="Supplier split expected but all charges have same owner",
            ))

    return issues


def run_pass3(extraction: dict, country_code: str | None = None) -> Pass3Result:
    """Run all validation checks."""
    issues: list[ValidationIssue] = []

    # Line item math
    for charge in extraction.get("charges", []):
        issue = validate_line_item_math(charge, country_code)
        if issue:
            issues.append(issue)

    # Totals
    issues.extend(validate_totals(extraction, country_code))

    # Meters
    issues.extend(validate_meters(extraction))

    # Logic
    issues.extend(validate_logic(extraction))

    # VAT validation (international)
    locale = extraction.get("extraction_metadata", {}).get("locale_context", {})
    if locale.get("tax_regime") in ("eu_vat", "uk_vat", "mx_iva"):
        vat_result = validate_vat(extraction)
        for vi in vat_result.issues:
            issues.append(ValidationIssue(
                field=f"vat.{vi['rule']}",
                severity=vi["severity"],
                message=vi["message"],
                expected=str(vi.get("expected")) if vi.get("expected") is not None else None,
                actual=str(vi.get("actual")) if vi.get("actual") is not None else None,
            ))

    # Gas conversion
    if extraction.get("classification", {}).get("commodity_type") == "natural_gas":
        gas_result = validate_gas_conversion(extraction)
        for gi in gas_result.issues:
            issues.append(ValidationIssue(
                field="meters.gas_conversion",
                severity=gi["severity"],
                message=gi["message"],
            ))

    # Determine overall disposition
    has_fatal = any(i.severity == "fatal" for i in issues)
    has_warning = any(i.severity == "warning" for i in issues)

    if has_fatal:
        disposition = MathDisposition.DISCREPANCY
    elif has_warning:
        disposition = MathDisposition.ROUNDING_VARIANCE
    else:
        disposition = MathDisposition.CLEAN

    return Pass3Result(issues=issues, math_disposition=disposition)


def _get_amount(obj) -> float | None:
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, dict):
        return obj.get("value")
    return None
