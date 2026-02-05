"""Test rounding tolerance per jurisdiction."""
import pytest
from invoice_ingestion.international.rounding_rules import get_rounding_tolerance, is_within_tolerance


class TestGetRoundingTolerance:
    def test_de_base(self):
        assert get_rounding_tolerance("DE") == 0.02

    def test_de_tax(self):
        assert get_rounding_tolerance("DE", is_tax=True) == 0.04

    def test_uk_base(self):
        assert get_rounding_tolerance("GB") == 0.01

    def test_fr_base(self):
        assert get_rounding_tolerance("FR") == 0.05

    def test_unknown_country_defaults(self):
        tolerance = get_rounding_tolerance("ZZ")
        assert tolerance == 0.05  # Default

    def test_us_base(self):
        assert get_rounding_tolerance("US") == 0.05


class TestIsWithinTolerance:
    def test_exact_match(self):
        assert is_within_tolerance(100.00, 100.00) is True

    def test_within_de(self):
        assert is_within_tolerance(100.00, 100.01, "DE") is True

    def test_outside_de(self):
        assert is_within_tolerance(100.00, 100.05, "DE") is False

    def test_within_uk(self):
        assert is_within_tolerance(100.00, 100.01, "GB") is True

    def test_outside_uk(self):
        assert is_within_tolerance(100.00, 100.02, "GB") is False
