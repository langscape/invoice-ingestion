"""Test VAT validation rules."""
import pytest
from invoice_ingestion.international.vat import validate_vat


class TestValidateVAT:
    def test_valid_line_vat(self):
        extraction = {
            "charges": [{
                "amount_net": {"value": 100.00},
                "vat_rate": 0.19,
                "vat_amount": {"value": 19.00},
                "amount_gross": {"value": 119.00},
            }],
            "totals": {},
        }
        result = validate_vat(extraction)
        assert result.passed

    def test_invalid_line_vat(self):
        extraction = {
            "charges": [{
                "amount_net": {"value": 100.00},
                "vat_rate": 0.19,
                "vat_amount": {"value": 25.00},  # Wrong
                "amount_gross": {"value": 125.00},
            }],
            "totals": {},
        }
        result = validate_vat(extraction)
        assert not result.passed

    def test_net_plus_vat_equals_gross(self):
        extraction = {
            "charges": [{
                "amount_net": {"value": 100.00},
                "vat_rate": 0.19,
                "vat_amount": {"value": 19.00},
                "amount_gross": {"value": 120.00},  # Should be 119
            }],
            "totals": {},
        }
        result = validate_vat(extraction)
        assert not result.passed

    def test_reverse_charge(self):
        extraction = {
            "charges": [{
                "amount_net": {"value": 100.00},
                "vat_rate": 0.0,
                "vat_amount": {"value": 0.00},
                "amount_gross": {"value": 100.00},
                "vat_category": "reverse_charge",
            }],
            "totals": {},
        }
        result = validate_vat(extraction)
        assert result.passed

    def test_total_validation(self):
        extraction = {
            "charges": [],
            "totals": {
                "total_net": {"value": 469.28},
                "total_vat": {"value": 87.67},
                "total_gross": {"value": 556.95},
            },
        }
        result = validate_vat(extraction)
        assert result.passed

    def test_total_mismatch(self):
        extraction = {
            "charges": [],
            "totals": {
                "total_net": {"value": 469.28},
                "total_vat": {"value": 87.67},
                "total_gross": {"value": 600.00},  # Wrong
            },
        }
        result = validate_vat(extraction)
        assert not result.passed
