"""Test locale detection."""
import pytest
from invoice_ingestion.international.locale_detection import (
    detect_currency, detect_country, detect_locale,
)


class TestDetectCurrency:
    def test_euro_symbol(self):
        assert detect_currency("Total: € 123,45") == "EUR"

    def test_gbp_symbol(self):
        assert detect_currency("Total: £99.99") == "GBP"

    def test_usd_symbol(self):
        assert detect_currency("Total: $1,234.56") == "USD"

    def test_no_currency(self):
        assert detect_currency("No currency here") is None


class TestDetectCountry:
    def test_gbp_means_gb(self):
        assert detect_country("invoice text", currency="GBP") == "GB"

    def test_de_from_language_currency(self):
        assert detect_country("", language="de", currency="EUR") == "DE"

    def test_fr_from_language_currency(self):
        assert detect_country("", language="fr", currency="EUR") == "FR"

    def test_de_keywords(self):
        result = detect_country("Netzentgelte Stromsteuer EEG Brennwert", language=None, currency=None)
        assert result == "DE"

    def test_fr_keywords(self):
        result = detect_country("TURPE CSPE TVA Abonnement Consommation", language=None, currency=None)
        assert result == "FR"


class TestDetectLocale:
    def test_german_invoice(self):
        text = "Netzentgelte: 45,67 €\nStromsteuer: 12,34 €\nBrutto: 58,01 €"
        result = detect_locale(text, language="de")
        assert result["country_code"] == "DE"
        assert result["currency_code"] == "EUR"
        assert result["tax_regime"] == "eu_vat"

    def test_us_invoice(self):
        text = "Energy Charge: $123.45\nSales tax: $5.67\nTotal: $129.12"
        result = detect_locale(text, language="en")
        assert result["currency_code"] == "USD"

    def test_number_format_eu(self):
        text = "Betrag: 1.234,56 €\nSumme: 5.678,90 €"
        result = detect_locale(text, language="de")
        assert result["number_format"] == "1.234,56"
        assert result["decimal_separator"] == ","
