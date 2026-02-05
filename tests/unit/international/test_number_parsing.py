"""Test locale-aware number parsing."""
import pytest
from invoice_ingestion.international.number_parsing import parse_amount, detect_number_format, strip_currency


class TestDetectNumberFormat:
    def test_eu_format(self):
        text = "Total: 1.234,56 EUR\nSubtotal: 567,89"
        assert detect_number_format(text) == "1.234,56"

    def test_us_format(self):
        text = "Total: $1,234.56\nSubtotal: $567.89"
        assert detect_number_format(text) == "1,234.56"

    def test_default_us(self):
        assert detect_number_format("no numbers here") == "1,234.56"


class TestParseAmount:
    def test_eu_format(self):
        assert parse_amount("1.234,56", "1.234,56") == 1234.56

    def test_us_format(self):
        assert parse_amount("1,234.56", "1,234.56") == 1234.56

    def test_eu_simple(self):
        assert parse_amount("1234,56", "1.234,56") == 1234.56

    def test_us_simple(self):
        assert parse_amount("1234.56", "1,234.56") == 1234.56

    def test_negative_parens(self):
        result = parse_amount("(23,66)", "1.234,56")
        assert result == -23.66

    def test_negative_trailing(self):
        result = parse_amount("23.66-", "1,234.56")
        assert result == -23.66

    def test_negative_leading(self):
        result = parse_amount("-23.66", "1,234.56")
        assert result == -23.66

    def test_currency_symbol_euro(self):
        result = parse_amount("€ 1.234,56", "1.234,56")
        assert result == 1234.56

    def test_currency_symbol_dollar(self):
        result = parse_amount("$1,234.56", "1,234.56")
        assert result == 1234.56

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_amount("", "1,234.56")

    def test_no_numeric_raises(self):
        with pytest.raises(ValueError):
            parse_amount("€", "1.234,56")

    def test_large_eu_number(self):
        assert parse_amount("12.345.678,90", "1.234,56") == 12345678.90


class TestStripCurrency:
    def test_euro_prefix(self):
        amount, currency = strip_currency("€ 123,45")
        assert currency == "EUR"
        assert amount == "123,45"

    def test_dollar_prefix(self):
        amount, currency = strip_currency("$1,234.56")
        assert currency == "USD"
        assert amount == "1,234.56"

    def test_gbp_prefix(self):
        amount, currency = strip_currency("£99.99")
        assert currency == "GBP"

    def test_iso_prefix(self):
        amount, currency = strip_currency("EUR 1.234,56")
        assert currency == "EUR"

    def test_no_currency(self):
        amount, currency = strip_currency("1234.56")
        assert currency is None
