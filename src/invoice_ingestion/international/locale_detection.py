"""Detect invoice locale from content signals."""
from __future__ import annotations
from .number_parsing import detect_number_format
from .date_parsing import detect_date_format
import re

# Currency → likely country mapping
CURRENCY_COUNTRY_MAP = {
    'EUR': None,  # Could be many countries
    'GBP': 'GB',
    'USD': 'US',
    'MXN': 'MX',
    'CHF': 'CH',
    'SEK': 'SE',
    'NOK': 'NO',
    'DKK': 'DK',
    'PLN': 'PL',
    'CZK': 'CZ',
    'HUF': 'HU',
    'BRL': 'BR',
}

# Language + currency → country
LANGUAGE_CURRENCY_COUNTRY = {
    ('de', 'EUR'): 'DE',
    ('fr', 'EUR'): 'FR',
    ('it', 'EUR'): 'IT',
    ('es', 'EUR'): 'ES',
    ('nl', 'EUR'): 'NL',
    ('pt', 'EUR'): 'PT',
    ('el', 'EUR'): 'GR',
    ('fi', 'EUR'): 'FI',
}

# Country-specific keywords
COUNTRY_KEYWORDS = {
    'DE': ['Netzentgelte', 'Stromsteuer', 'EEG', 'Brennwert', 'Zustandszahl', 'Grundpreis', 'Arbeitspreis', 'BNetzA', 'Zähler'],
    'FR': ['TURPE', 'CSPE', 'TCFE', 'CTA', 'TVA', 'Abonnement', 'Consommation', 'PDL', 'Heures Pleines', 'Heures Creuses'],
    'ES': ['Peaje', 'IVA', 'CUPS', 'Potencia contratada', 'Energía activa', 'Impuesto'],
    'IT': ['Oneri di sistema', 'IVA', 'POD', 'Accisa', 'Imposte', 'Trasporto', 'Gestione contatore'],
    'UK': ['CCL', 'DUoS', 'TNUoS', 'BSUoS', 'MPAN', 'Capacity Market', 'Standing charge', 'pence per kWh'],
    'GB': ['CCL', 'DUoS', 'TNUoS', 'BSUoS', 'MPAN', 'Capacity Market', 'Standing charge', 'pence per kWh'],
    'NL': ['Energiebelasting', 'ODE', 'Transportkosten', 'EAN', 'Vastrecht', 'Leveringskosten'],
    'MX': ['CFE', 'DAC', 'CFDI', 'IVA', 'DAP', 'Factor de potencia'],
    'US': ['kWh', 'therms', 'CCF', 'MCF', 'Sales tax', 'Franchise fee', 'Delivery charges'],
}

def detect_currency(text: str) -> str | None:
    """Detect currency from text."""
    if '€' in text or 'EUR' in text:
        return 'EUR'
    if '£' in text or 'GBP' in text:
        return 'GBP'
    if '$' in text:
        if 'MXN' in text or 'MX$' in text:
            return 'MXN'
        if 'R$' in text:
            return 'BRL'
        return 'USD'
    for code in ['CHF', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF']:
        if code in text:
            return code
    return None

def detect_country(text: str, language: str | None = None, currency: str | None = None) -> str | None:
    """Detect country from text content, language, and currency signals."""
    # Direct currency → country
    if currency and currency in CURRENCY_COUNTRY_MAP and CURRENCY_COUNTRY_MAP[currency] is not None:
        return CURRENCY_COUNTRY_MAP[currency]

    # Language + currency
    if language and currency and (language, currency) in LANGUAGE_CURRENCY_COUNTRY:
        return LANGUAGE_CURRENCY_COUNTRY[(language, currency)]

    # Keyword matching
    scores: dict[str, int] = {}
    text_upper = text.upper()
    for country, keywords in COUNTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.upper() in text_upper)
        if score > 0:
            scores[country] = score

    if scores:
        return max(scores, key=scores.get)

    return None

def detect_locale(text: str, language: str | None = None) -> dict:
    """Full locale detection. Returns dict with country, currency, formats, etc."""
    currency = detect_currency(text)
    country = detect_country(text, language=language, currency=currency)
    number_format = detect_number_format(text)
    date_format_str = detect_date_format(text)

    # Determine tax regime
    tax_regime = "us_sales_tax"
    if country in ('DE', 'FR', 'ES', 'IT', 'NL', 'PT', 'GR', 'FI', 'AT', 'BE', 'IE'):
        tax_regime = "eu_vat"
    elif country == 'GB':
        tax_regime = "uk_vat"
    elif country == 'MX':
        tax_regime = "mx_iva"

    # Market model
    market_model = "regulated"
    if country in ('DE', 'FR', 'ES', 'IT', 'NL', 'GB', 'AT', 'BE', 'FI', 'SE', 'NO', 'DK'):
        market_model = "liberalized_eu"
    elif country == 'US':
        market_model = "deregulated"  # simplified; varies by state

    # Currency info
    decimal_sep = "," if number_format == "1.234,56" else "."
    thousands_sep = "." if number_format == "1.234,56" else ","

    return {
        "country_code": country,
        "language": language or "en",
        "currency_code": currency or "USD",
        "currency_symbol": _get_currency_symbol(currency),
        "decimal_separator": decimal_sep,
        "thousands_separator": thousands_sep,
        "date_format": date_format_str,
        "number_format": number_format,
        "tax_regime": tax_regime,
        "market_model": market_model,
    }

def _get_currency_symbol(currency: str | None) -> str:
    symbols = {'EUR': '€', 'GBP': '£', 'USD': '$', 'MXN': '$', 'CHF': 'CHF', 'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr'}
    return symbols.get(currency or 'USD', '$')
