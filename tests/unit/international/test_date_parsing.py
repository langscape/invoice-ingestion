"""Test locale-aware date parsing."""
import pytest
from datetime import date
from invoice_ingestion.international.date_parsing import (
    parse_date, detect_date_format, is_date_ambiguous, validate_billing_period,
)


class TestDetectDateFormat:
    def test_dot_format(self):
        assert detect_date_format("15.03.2024") == "DD.MM.YYYY"

    def test_iso_format(self):
        assert detect_date_format("2024-03-15") == "YYYY-MM-DD"

    def test_unambiguous_dd_mm(self):
        assert detect_date_format("15/03/2024") == "DD/MM/YYYY"

    def test_unambiguous_mm_dd(self):
        assert detect_date_format("03/15/2024") == "MM/DD/YYYY"


class TestParseDate:
    def test_iso(self):
        assert parse_date("2024-03-15") == date(2024, 3, 15)

    def test_dot_format(self):
        assert parse_date("15.03.2024", "DD.MM.YYYY") == date(2024, 3, 15)

    def test_dd_mm_yyyy(self):
        assert parse_date("15/03/2024", "DD/MM/YYYY") == date(2024, 3, 15)

    def test_mm_dd_yyyy(self):
        assert parse_date("03/15/2024", "MM/DD/YYYY") == date(2024, 3, 15)

    def test_ambiguous_with_locale_de(self):
        # 05.03.2024 with DD.MM.YYYY = March 5
        assert parse_date("05.03.2024", "DD.MM.YYYY") == date(2024, 3, 5)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_date("not-a-date", "MM/DD/YYYY")


class TestIsDateAmbiguous:
    def test_unambiguous_day_gt_12(self):
        assert is_date_ambiguous("15/03/2024") is False

    def test_ambiguous_both_valid(self):
        assert is_date_ambiguous("05/03/2024") is True

    def test_same_values_not_ambiguous(self):
        assert is_date_ambiguous("03/03/2024") is False

    def test_non_slash_format(self):
        assert is_date_ambiguous("2024-03-15") is False


class TestValidateBillingPeriod:
    def test_normal_period(self):
        valid, msg = validate_billing_period(date(2024, 1, 1), date(2024, 1, 31))
        assert valid is True
        assert msg is None

    def test_negative_period(self):
        valid, msg = validate_billing_period(date(2024, 2, 1), date(2024, 1, 1))
        assert valid is False
        assert "negative" in msg.lower()

    def test_zero_period(self):
        valid, msg = validate_billing_period(date(2024, 1, 1), date(2024, 1, 1))
        assert valid is False

    def test_very_long_period(self):
        valid, msg = validate_billing_period(date(2023, 1, 1), date(2024, 6, 1))
        assert valid is False

    def test_short_period_warning(self):
        valid, msg = validate_billing_period(date(2024, 1, 1), date(2024, 1, 10))
        assert valid is True
        assert msg is not None and "short" in msg.lower()
