"""Test Pass 3 validation rules -- the most comprehensive test file."""
import pytest
from invoice_ingestion.passes.pass3_validation import (
    validate_line_item_math, validate_totals, validate_meters, validate_logic, run_pass3,
)
from tests.factories import make_charge, make_meter, make_extraction_dict


class TestValidateLineItemMath:
    def test_exact_match(self):
        charge = make_charge("L001", "energy", 23.66, 280, 0.0845)
        result = validate_line_item_math(charge)
        assert result is None  # Clean

    def test_rounding_tolerance(self):
        charge = make_charge("L001", "energy", 23.67, 280, 0.0845)  # Off by 0.01
        result = validate_line_item_math(charge)
        assert result is None or result.severity == "info"

    def test_no_qty_rate(self):
        charge = make_charge("L001", "fixed", 15.00, None, None)
        result = validate_line_item_math(charge)
        assert result is None

    def test_discrepancy(self):
        charge = make_charge("L001", "energy", 50.00, 280, 0.0845)  # Way off
        result = validate_line_item_math(charge)
        assert result is not None
        assert result.severity == "warning"

    def test_minimum_bill(self):
        charge = make_charge("L001", "fixed", 25.00, 100, 0.10)  # stated > expected
        result = validate_line_item_math(charge)
        # Should detect possible minimum bill
        assert result is not None

    def test_utility_adjustment(self):
        # Within 2% but beyond rounding
        charge = make_charge("L001", "energy", 100.50, 1000, 0.10)  # Expected 100.00
        result = validate_line_item_math(charge)
        assert result is not None
        assert result.severity == "info"


class TestValidateTotals:
    def test_matching_totals(self):
        extraction = make_extraction_dict(
            charges=[
                make_charge("L001", "energy", 98.20, section="supply"),
                make_charge("L002", "rider", 67.15, section="distribution"),
                make_charge("L003", "tax", 22.10, None, None, section="taxes"),
            ],
            current_charges=187.45,
        )
        issues = validate_totals(extraction)
        assert all(i.severity != "warning" for i in issues)

    def test_section_mismatch(self):
        extraction = make_extraction_dict(
            charges=[make_charge("L001", "energy", 50.00, section="supply")],
            current_charges=187.45,
        )
        extraction["totals"]["supply_subtotal"] = {"value": 100.00}  # Mismatch
        issues = validate_totals(extraction)
        assert any(i.severity == "warning" for i in issues)

    def test_total_mismatch(self):
        extraction = make_extraction_dict(
            charges=[make_charge("L001", "energy", 50.00)],
            current_charges=200.00,
        )
        issues = validate_totals(extraction)
        assert any("mismatch" in i.message.lower() or "total" in i.message.lower() for i in issues)


class TestValidateMeters:
    def test_valid_read_diff(self):
        meter = make_meter(consumption=750.0, prev_read=45230, curr_read=45980)
        extraction = make_extraction_dict(meters=[meter])
        issues = validate_meters(extraction)
        assert len(issues) == 0

    def test_read_diff_mismatch(self):
        meter = make_meter(consumption=500.0, prev_read=45230, curr_read=45980)  # Actual diff is 750
        extraction = make_extraction_dict(meters=[meter])
        issues = validate_meters(extraction)
        assert len(issues) > 0

    def test_tou_sums(self):
        tou = [
            {"consumption": {"value": 280, "unit": "kWh"}},
            {"consumption": {"value": 470, "unit": "kWh"}},
        ]
        meter = make_meter(consumption=750.0, tou=tou)
        extraction = make_extraction_dict(meters=[meter])
        issues = validate_meters(extraction)
        assert len(issues) == 0

    def test_tou_mismatch(self):
        tou = [
            {"consumption": {"value": 280, "unit": "kWh"}},
            {"consumption": {"value": 200, "unit": "kWh"}},  # Sum=480, total=750
        ]
        meter = make_meter(consumption=750.0, tou=tou)
        extraction = make_extraction_dict(meters=[meter])
        issues = validate_meters(extraction)
        assert any("TOU" in i.message or "tou" in i.message.lower() for i in issues)

    def test_with_multiplier(self):
        meter = make_meter(consumption=7500.0, prev_read=45230, curr_read=45980, multiplier=10.0)
        extraction = make_extraction_dict(meters=[meter])
        issues = validate_meters(extraction)
        assert len(issues) == 0


class TestValidateLogic:
    def test_gas_units_on_electric(self):
        meter = make_meter(unit="therms")
        extraction = make_extraction_dict(meters=[meter], commodity="electricity")
        issues = validate_logic(extraction)
        assert any(i.severity == "fatal" for i in issues)

    def test_extreme_billing_period(self):
        extraction = make_extraction_dict()
        extraction["invoice"]["billing_period"]["days"] = 120
        issues = validate_logic(extraction)
        assert any("billing period" in i.message.lower() for i in issues)

    def test_negative_on_non_credit(self):
        charge = make_charge("L001", "energy", -50.00, None, None)
        extraction = make_extraction_dict(charges=[charge])
        issues = validate_logic(extraction)
        assert any("negative" in i.message.lower() for i in issues)

    def test_negative_on_credit_ok(self):
        charge = make_charge("L001", "credit", -50.00, None, None)
        extraction = make_extraction_dict(charges=[charge])
        issues = validate_logic(extraction)
        assert not any("negative" in i.message.lower() for i in issues)

    def test_demand_expected_but_missing(self):
        extraction = make_extraction_dict()
        extraction["classification"]["has_demand_charges"] = True
        issues = validate_logic(extraction)
        assert any("demand" in i.message.lower() for i in issues)

    def test_tou_expected_but_missing(self):
        extraction = make_extraction_dict()
        extraction["classification"]["has_tou"] = True
        issues = validate_logic(extraction)
        assert any("TOU" in i.message or "tou" in i.message.lower() for i in issues)

    def test_supplier_split_expected_but_single_owner(self):
        extraction = make_extraction_dict()
        extraction["classification"]["has_supplier_split"] = True
        issues = validate_logic(extraction)
        assert any("supplier" in i.message.lower() or "owner" in i.message.lower() for i in issues)


class TestRunPass3:
    def test_clean_extraction(self):
        extraction = make_extraction_dict()
        result = run_pass3(extraction)
        assert result.math_disposition in ("clean", "rounding_variance")

    def test_with_fatal(self):
        meter = make_meter(unit="therms")
        extraction = make_extraction_dict(meters=[meter], commodity="electricity")
        result = run_pass3(extraction)
        assert result.math_disposition == "discrepancy"
        assert any(i.severity == "fatal" for i in result.issues)
