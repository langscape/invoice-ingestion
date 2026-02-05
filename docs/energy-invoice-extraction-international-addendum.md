# Energy Invoice Extraction — International Markets Addendum (v2 → v3)

## Revision Summary

| Area | Change |
|---|---|
| Number formatting | Full locale-aware parsing: `1.234,56` (EU) vs `1,234.56` (US/UK). Decimal/thousand separator detection is now a Pass 0 responsibility. |
| Currency | Multi-currency schema with ISO 4217 codes. No assumed USD. Exchange rate capture for cross-border invoices. |
| VAT / Tax structure | European tax model added: net amount → VAT rate → gross amount. Reverse charge mechanism. Multiple VAT rates on single invoice. Tax ID (VAT number) extraction. |
| Units | Added m³ (gas), MWh, GJ. European gas commonly in m³ or kWh (energy-converted). Calorific value / conversion factor extraction. |
| Market structure | European liberalized market concepts: network operator vs. supplier vs. metering operator (can be three separate entities). Grid fees, energy taxes, renewable levies (EEG, CSPE, etc.). |
| Regulatory charges | Country-specific levies that have no US equivalent: EEG-Umlage (DE), CSPE/TURPE (FR), CCL (UK), capacity mechanism charges, green certificates. |
| Invoice standards | Awareness of Factur-X / ZUGFeRD (DE/FR), FatturaPA (IT), SII (ES). Structured data embedded in PDF — extractable without vision. |
| Date formats | DD/MM/YYYY vs MM/DD/YYYY disambiguation. ISO-8601 as canonical. |
| Address formats | European address conventions (postcode before city in DE/NL, after in UK/FR). |

---

## 1. European Energy Market — Domain Knowledge

### 1.1 Market Structure Differences

The fundamental structure of European energy markets differs from the US in ways that directly affect invoice extraction.

| Concept | US Model | European Model | Extraction Impact |
|---|---|---|---|
| **Market participants** | Utility + Supplier (2 parties max) | Network Operator (DSO/TSO) + Supplier + Metering Operator (up to 3 separate entities) | Must handle 3-way charge attribution, not just 2. |
| **Invoice issuance** | Often consolidated (utility bills for both) | Supplier invoices for energy + pass-through network charges. Some markets: separate DSO invoice. | May need to link two invoices for one service point. |
| **Regulation** | State-level (50 regulatory regimes) | Country-level + EU directives. Each country has its own regulator (BNetzA, CRE, Ofgem, CNMC, ARERA, etc.) | Regulatory charge names are country-specific. |
| **Metering** | Utility-owned meter, monthly reads common | Smart meter rollout varies wildly. Monthly, bi-monthly, quarterly, semi-annual, or annual reads depending on country and meter type. | Billing period can be up to 12 months. Interim invoices (estimated) + annual true-up is common. |
| **Unit convention (gas)** | Therms, CCF, MCF | m³ (volume) converted to kWh or MWh using a **calorific value** (CV) / conversion factor. Some countries bill in kWh directly. | Must extract the calorific value/conversion factor. It changes monthly. |
| **Unit convention (electricity)** | kWh | kWh for small consumers, MWh for commercial/industrial | Normalize to kWh or MWh consistently. |

### 1.2 Electricity — European-Specific Concepts

| Concept | Countries | What It Means | Why Extraction Cares |
|---|---|---|---|
| **Network/Grid Charges (Netzentgelte, TURPE, DUoS/TNUoS)** | All EU | Charges for using the distribution and transmission grid. Often broken into capacity (kW) and energy (kWh) components. | These replace the US "distribution" concept but are structured differently. |
| **Energy Tax / Electricity Tax** | DE, NL, DK, etc. | Government-imposed tax per kWh consumed. Different from VAT. | Separate line item. Tax rate is per-unit, not percentage. |
| **EEG-Umlage / Renewable Levy** | DE (historically), similar in other countries | Surcharge to fund renewable energy subsidies. In Germany, was the single largest surcharge until 2022 reform. | May be zero in current period but still listed. Historical invoices will have significant amounts. |
| **Capacity Mechanism Charges** | UK, FR, others | Charges to fund generation capacity availability. In UK: Capacity Market charges. In FR: part of TURPE. | Often calculated on a different basis than energy charges. |
| **Climate Change Levy (CCL)** | UK | Tax on energy delivered to business consumers. Different rates for electricity vs. gas. Exemptions for renewable sources (with LECs). | Must detect CCL and check if exemption certificates (LECs/REGOs) reduce it. |
| **Feed-in Tariff / Self-Consumption** | All EU | More complex than US net metering. Feed-in tariff (fixed price for exported kWh), self-consumption bonus, virtual net metering across multiple sites. | Multiple generation-related credit mechanisms possible on one invoice. |
| **Reactive Power Charges** | ES, IT, FR, DE, etc. | More commonly billed in Europe than US. Based on tan(φ) or cos(φ). Penalty thresholds vary by country. | Must capture the power factor metric and threshold. |
| **Contracted Power / Puissance Souscrite** | FR, ES, IT | Customer contracts for a maximum power level (kVA). Exceeding it incurs penalty charges. Different from US demand charges. | This is a capacity subscription, not a measured peak. Must distinguish from metered demand. |
| **Time Periods (varies by country)** | All EU | FR: Heures Pleines/Heures Creuses (HP/HC) or Tempo (Bleu/Blanc/Rouge × HP/HC = 6 tiers). ES: Periods P1-P6. IT: F1/F2/F3. DE: HT/NT. | Country-specific TOU tier names. Must map to standardized representation. |
| **Green Certificates / Guarantees of Origin** | All EU | Certificates proving renewable source. May appear as a line item or reduce certain taxes. | Extract if present; affects CCL and other tax calculations. |

### 1.3 Natural Gas — European-Specific Concepts

| Concept | Countries | What It Means | Why Extraction Cares |
|---|---|---|---|
| **Calorific Value (CV) / Brennwert / PCS** | All EU | Converts volume (m³) to energy (kWh). Varies by region and month. Shown on invoice as a coefficient. | **Critical.** Without the CV, you cannot validate consumption in kWh. Formula: m³ × CV × correction factor = kWh. |
| **Volume Correction Factor / Zustandszahl** | DE, AT, NL | Adjusts metered volume for temperature and pressure to standard conditions. | Another multiplier in the chain. Must capture. |
| **Gas in kWh** | DE, FR, NL, UK, etc. | Final billing is in kWh (or MWh), not volume. The invoice may show volume AND energy, or just energy. | Must handle both representations and the conversion between them. |
| **Standing Charge / Grundpreis** | All EU | Fixed daily or monthly fee. In DE, often shown as an annual amount prorated to the billing period. | Must handle proration and annualized vs. period amounts. |
| **Gas Levy / Carbon Tax** | Various | Country-specific: UK Carbon Price Support, DE CO2-Abgabe, FR TICGN. | Per-kWh or per-m³ tax, separate from VAT. |

### 1.4 Water — European-Specific Concepts

| Concept | Countries | What It Means | Why Extraction Cares |
|---|---|---|---|
| **Water + Wastewater + Stormwater** | All EU | Often three separate services, sometimes on one invoice, sometimes separate. | Must split three ways, not just two. |
| **Standing Charge by Meter Size** | All EU | Similar to US but meter sizes in metric (DN15, DN20, DN25, etc.) | Different size conventions than US (5/8", 3/4", etc.) |
| **Assainissement (FR) / Abwasser (DE)** | FR, DE | Wastewater charges, sometimes calculated as a percentage of water consumption, sometimes separately metered. | The ratio may not be 1:1. Must capture the calculation basis. |
| **Redevances (FR)** | FR | Multiple government fees: redevance pollution, redevance modernisation, redevance prélèvement. | 4-5 separate regulatory charges unique to French water invoices. |
| **m³ as standard unit** | All EU | European water is billed in cubic meters, not gallons or CCF. | Normalize differently than US. |

### 1.5 VAT & Tax Structure — Europe

This is fundamentally different from US tax structures and needs special handling.

| Concept | Detail | Extraction Impact |
|---|---|---|
| **VAT (Value Added Tax)** | Applied as a percentage to the net amount. Standard rates: DE 19%, FR 20%, IT 22%, ES 21%, UK 20%, NL 21%. Reduced rates may apply to energy. | Must extract: net amount, VAT rate(s), VAT amount(s), gross amount. |
| **Multiple VAT rates on one invoice** | Some charges may be at standard rate, others at reduced rate (e.g., FR: water at 5.5%, wastewater at 10%, fees at 20%). | Must map each charge (or group of charges) to its applicable VAT rate. |
| **Reverse Charge Mechanism** | For B2B cross-border transactions, VAT liability shifts to the buyer. Invoice shows "Reverse charge" and 0% VAT. | Must detect reverse charge and not flag 0% VAT as an error. |
| **VAT Number / Tax ID** | European invoices must show the supplier's VAT number. B2B invoices show both parties' VAT numbers. | Extract both. Useful for validation and compliance. |
| **Net + VAT = Gross** | The canonical European invoice equation. US invoices often don't separate pre-tax and post-tax as cleanly. | Must validate: Σ(net line items) × (1 + VAT rate) ≈ gross total. Handle multiple VAT rates. |
| **Tax-on-tax** | Some countries apply certain levies before VAT is calculated, meaning VAT is charged on the levy. Others exempt levies from VAT. | Must understand the tax calculation order per jurisdiction. |
| **Energy Tax / Excise Duty** | Per-unit tax (e.g., €/kWh). Applied before VAT in most countries. | This is NOT VAT. It's a separate line item that VAT is then applied to. |
| **Eco-taxes and special levies** | Country-specific environmental, nuclear, renewable, or social levies. | Each is a separate extraction target. |

---

## 2. Schema Changes for International Support

### 2.1 New Top-Level: Locale Context

Add to `extraction_metadata`:

```json
{
  "locale_context": {
    "country_code": "DE",
    "country_name": "Germany",
    "language": "de",
    "currency": {
      "code": "EUR",
      "symbol": "€",
      "decimal_separator": ",",
      "thousands_separator": "."
    },
    "date_format_detected": "DD.MM.YYYY",
    "number_format_detected": "1.234,56",
    "tax_regime": "eu_vat",
    "regulatory_body": "BNetzA",
    "market_model": "liberalized_eu"
  }
}
```

### 2.2 Updated Amount Fields — Multi-Currency

Every monetary amount changes from a simple value to:

```json
{
  "amount": {
    "value": 23.66,
    "currency": "EUR",
    "original_string": "23,66 €",
    "confidence": 0.96,
    "source_location": "page2:line4:col-amount"
  }
}
```

The `original_string` preserves exactly what was printed on the invoice — critical for traceability when the extraction involves locale-specific number parsing.

### 2.3 Updated Charge Line — VAT & Tax Attribution

Each charge line gains:

```json
{
  "line_id": "L001",
  "description": { "value": "Arbeitspreis HT", "translated": "Energy Charge Peak", "confidence": 0.94 },
  "amount_net": { "value": 23.66, "currency": "EUR", "original_string": "23,66" },
  "vat_rate": 0.19,
  "vat_amount": { "value": 4.50, "currency": "EUR" },
  "amount_gross": { "value": 28.16, "currency": "EUR" },
  "vat_category": "standard | reduced | zero | exempt | reverse_charge",
  "tax_calculation_order": "pre_vat",
  "...": "...all other existing fields..."
}
```

### 2.4 New: VAT Summary Block

Add to `totals`:

```json
{
  "vat_summary": [
    {
      "vat_rate": 0.19,
      "vat_category": "standard",
      "taxable_base": { "value": 456.78, "currency": "EUR" },
      "vat_amount": { "value": 86.79, "currency": "EUR" }
    },
    {
      "vat_rate": 0.07,
      "vat_category": "reduced",
      "taxable_base": { "value": 12.50, "currency": "EUR" },
      "vat_amount": { "value": 0.88, "currency": "EUR" }
    }
  ],
  "total_net": { "value": 469.28, "currency": "EUR" },
  "total_vat": { "value": 87.67, "currency": "EUR" },
  "total_gross": { "value": 556.95, "currency": "EUR" },
  "total_amount_due": { "value": 556.95, "currency": "EUR" },
  "reverse_charge_applied": false,
  "vat_numbers": {
    "supplier_vat": "DE123456789",
    "customer_vat": "DE987654321"
  }
}
```

### 2.5 Updated Meter Block — Calorific Value

For gas meters, add:

```json
{
  "meter_number": { "value": "G-001" },
  "consumption_volume": {
    "raw_value": 1250,
    "raw_unit": "m³",
    "previous_read": 45230,
    "current_read": 46480
  },
  "conversion_factors": {
    "calorific_value": { "value": 11.2, "unit": "kWh/m³", "source_location": "page2:conversion-table" },
    "volume_correction_factor": { "value": 0.9626, "source_location": "page2:conversion-table" },
    "conversion_formula": "1250 m³ × 0.9626 × 11.2 kWh/m³ = 13,474.4 kWh"
  },
  "consumption_energy": {
    "value": 13474.4,
    "unit": "kWh",
    "note": "Derived from volume × correction factor × calorific value"
  },
  "...": "...existing fields..."
}
```

### 2.6 Updated Account Block — European Identifiers

```json
{
  "account": {
    "account_number": { "value": "..." },
    "contract_number": { "value": "V-2024-12345", "note": "European suppliers often use contract numbers distinct from account numbers" },
    "customer_name": { "value": "..." },
    "customer_vat_number": { "value": "DE987654321" },
    "service_address": { "value": "..." },
    "pod_pdr": { "value": "FR00123456789012", "note": "Point of Delivery (electricity: POD/PDL, gas: PDR/PCE). Unique national identifier for the connection point." },
    "ean_code": { "value": "5412345678901234567", "note": "EAN/GSRN code used in some markets (BE, NL) as meter/connection identifier" },
    "utility_provider": { "value": "..." },
    "network_operator": { "value": "Enedis", "note": "DSO — may differ from supplier. In EU, this is always a separate entity." },
    "metering_operator": { "value": "Enedis", "note": "Usually same as DSO but can differ" },
    "supplier": { "value": "TotalEnergies" }
  }
}
```

### 2.7 New: Contracted Power / Subscribed Capacity

Add to meters (European electricity):

```json
{
  "contracted_capacity": {
    "value": 36,
    "unit": "kVA",
    "exceeded": false,
    "excess_penalty_amount": null,
    "note": "Puissance Souscrite (FR) / Potencia Contratada (ES). Not a metered demand — a contractual limit."
  },
  "contracted_capacity_by_period": [
    { "period": "P1", "value": 36, "unit": "kVA" },
    { "period": "P2", "value": 36, "unit": "kVA" },
    { "period": "P3", "value": 20, "unit": "kVA" }
  ]
}
```

### 2.8 Updated Classification — Market Model

```json
{
  "classification": {
    "...": "...existing fields...",
    "market_model": "us_regulated | us_deregulated | eu_liberalized | eu_regulated | uk_liberalized | other",
    "country_code": "DE",
    "has_vat_structure": true,
    "has_reverse_charge": false,
    "has_calorific_conversion": true,
    "has_contracted_capacity": true,
    "has_multiple_vat_rates": true,
    "has_structured_invoice_data": false,
    "structured_format": null,
    "tou_naming_convention": "DE_HT_NT | FR_HP_HC | FR_TEMPO | ES_P1_P6 | IT_F1_F3 | generic"
  }
}
```

---

## 3. Pass 0 Changes — Locale Detection & Number Parsing

### 3.1 Locale Detection (add to Pass 0)

Before any extraction, detect the invoice's locale. This drives everything downstream.

```python
def detect_locale(extracted_text, page_images):
    """Detect country, language, currency, and number format from invoice."""

    # Step 1: Language detection (existing)
    language = detect_language(extracted_text)

    # Step 2: Currency detection
    currency_patterns = {
        'EUR': [r'€', r'EUR\b'],
        'GBP': [r'£', r'GBP\b'],
        'USD': [r'\$', r'USD\b'],
        'CHF': [r'CHF\b'],
        'SEK': [r'SEK\b', r'kr\b'],
        'DKK': [r'DKK\b'],
        'NOK': [r'NOK\b'],
        'PLN': [r'PLN\b', r'zł'],
        'CZK': [r'CZK\b', r'Kč'],
        'MXN': [r'MXN\b', r'\$'],  # Disambiguate from USD via language
    }
    currency = detect_currency(extracted_text, currency_patterns, language)

    # Step 3: Number format detection
    # This is CRITICAL and subtle
    number_format = detect_number_format(extracted_text)

    # Step 4: Date format detection
    date_format = detect_date_format(extracted_text)

    # Step 5: Country inference
    country = infer_country(language, currency, extracted_text)

    return LocaleContext(
        country_code=country,
        language=language,
        currency=currency,
        decimal_separator=number_format.decimal,
        thousands_separator=number_format.thousands,
        date_format=date_format
    )


def detect_number_format(text):
    """
    Detect whether the invoice uses comma-decimal or dot-decimal.

    This is the single hardest locale problem. Examples:
      "1.234,56" → EU format (decimal comma, dot thousands)
      "1,234.56" → US/UK format (decimal dot, comma thousands)
      "1234,56"  → EU format (no thousands separator)
      "1234.56"  → Ambiguous if no other context

    Strategy:
    1. Find monetary amounts (near currency symbols or in table columns).
    2. Look for the LAST separator before end of number.
    3. If last separator is followed by exactly 2 digits → likely decimal.
    4. If last separator is followed by exactly 3 digits → likely thousands.
    5. Cross-validate across multiple amounts on the invoice.
    6. If still ambiguous, use language/country as tiebreaker.
    """
    amounts = extract_candidate_amounts(text)

    # Pattern analysis
    comma_decimal_evidence = 0
    dot_decimal_evidence = 0

    for amount_str in amounts:
        # "23,66" or "1.234,56" → comma is decimal
        if re.search(r',\d{2}$', amount_str):
            comma_decimal_evidence += 1
        # "23.66" or "1,234.56" → dot is decimal
        if re.search(r'\.\d{2}$', amount_str):
            dot_decimal_evidence += 1
        # "1.234.567" → dots are thousands (EU)
        if re.search(r'\.\d{3}\.', amount_str):
            comma_decimal_evidence += 3  # Strong signal
        # "1,234,567" → commas are thousands (US)
        if re.search(r',\d{3},', amount_str):
            dot_decimal_evidence += 3

    if comma_decimal_evidence > dot_decimal_evidence:
        return NumberFormat(decimal=',', thousands='.')
    elif dot_decimal_evidence > comma_decimal_evidence:
        return NumberFormat(decimal='.', thousands=',')
    else:
        # Fall back to language/country
        return infer_number_format_from_locale(language, country)
```

### 3.2 Number Parsing (used in all downstream passes)

```python
def parse_amount(raw_string, locale_context):
    """
    Parse a monetary amount string according to detected locale.

    Returns a canonical float + original string for traceability.
    """
    decimal_sep = locale_context.currency.decimal_separator
    thousands_sep = locale_context.currency.thousands_separator

    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[€$£CHF\s]', '', raw_string.strip())

    # Remove thousands separator
    if thousands_sep:
        cleaned = cleaned.replace(thousands_sep, '')

    # Replace decimal separator with dot
    if decimal_sep == ',':
        cleaned = cleaned.replace(',', '.')

    # Handle negative: could be "-23.66", "(23.66)", "23.66-", "23,66-"
    is_negative = False
    if cleaned.startswith('-') or cleaned.startswith('('):
        is_negative = True
        cleaned = cleaned.strip('-()').strip()
    if cleaned.endswith('-'):
        is_negative = True
        cleaned = cleaned.rstrip('-').strip()

    try:
        value = float(cleaned)
        if is_negative:
            value = -value
        return ParsedAmount(
            value=value,
            original_string=raw_string,
            parsing_confidence=0.95 if locale_context.number_format_confidence > 0.8 else 0.75
        )
    except ValueError:
        return ParsedAmount(value=None, original_string=raw_string, parsing_confidence=0.0,
                           error=f"Could not parse '{raw_string}' with locale {locale_context}")
```

### 3.3 Date Parsing

```python
def parse_date(raw_string, locale_context):
    """
    Parse dates with awareness of DD/MM/YYYY vs MM/DD/YYYY ambiguity.

    "05/03/2024" = March 5 (US) or May 3 (EU). This MATTERS.
    """
    date_format = locale_context.date_format_detected

    # Try detected format first
    for fmt in get_format_candidates(date_format):
        try:
            parsed = datetime.strptime(raw_string.strip(), fmt)

            # Sanity check: is this date reasonable for a billing period?
            if parsed.year < 2000 or parsed.year > 2030:
                continue

            return ParsedDate(
                value=parsed.strftime('%Y-%m-%d'),  # Canonical ISO-8601
                original_string=raw_string,
                format_used=fmt,
                ambiguous=is_date_ambiguous(raw_string)
            )
        except ValueError:
            continue

    return ParsedDate(value=None, original_string=raw_string, error="Unparseable")


def is_date_ambiguous(date_string):
    """
    Is this date ambiguous between DD/MM and MM/DD?
    "15/03/2024" is NOT ambiguous (15 can't be a month).
    "05/03/2024" IS ambiguous.
    """
    parts = re.split(r'[/.\-]', date_string)
    if len(parts) >= 2:
        a, b = int(parts[0]), int(parts[1])
        if a <= 12 and b <= 12:
            return True  # Both could be months
    return False
```

### 3.4 Structured Invoice Detection (Factur-X / ZUGFeRD / FatturaPA)

European invoices increasingly embed structured XML data inside the PDF.

```python
def check_structured_invoice(pdf_path):
    """
    Check if PDF contains embedded structured invoice data.
    If so, extract it — this is MORE reliable than vision extraction.
    """
    # Factur-X / ZUGFeRD: XML embedded as PDF attachment
    attachments = extract_pdf_attachments(pdf_path)
    for attachment in attachments:
        if attachment.name in ['factur-x.xml', 'zugferd-invoice.xml',
                               'ZUGFeRD-invoice.xml', 'xrechnung.xml']:
            return StructuredInvoice(
                format='factur-x',
                xml_data=parse_xml(attachment.data),
                confidence=0.99  # Machine-generated data — very high trust
            )

    # FatturaPA (Italy): separate XML file
    # SII (Spain): separate XML
    # These are typically not embedded in PDF but delivered alongside

    return None
```

**When structured data is found:** Use it as the **primary source** and use vision extraction as the **verification**. This inverts the normal flow — vision becomes the audit, structured data is ground truth.

---

## 4. Pass 0.5 Changes — Classification Updates

Add to the classification prompt:

```
Additional classification questions for international invoices:

7. COUNTRY / JURISDICTION: Which country is this invoice from?
   Look for: language, currency symbol, VAT numbers, regulatory references,
   utility company name, address format.

8. NUMBER FORMAT: Does this invoice use comma-decimal (1.234,56) or
   dot-decimal (1,234.56)?

9. TAX STRUCTURE:
   - Is VAT shown separately? If so, how many VAT rates are applied?
   - Is there a "reverse charge" notation?
   - Are there per-unit energy taxes separate from VAT?

10. GAS CONVERSION: For gas invoices, is a calorific value or conversion
    factor shown? Is billing in volume (m³) or energy (kWh)?

11. EUROPEAN IDENTIFIERS: Are any of these present?
    - POD/PDL/PDR/PCE (delivery point ID)
    - EAN/GSRN code
    - Contract number (separate from account number)
    - CUPS (Spain), POD (Italy), PDL (France)

12. CONTRACTED CAPACITY: Is there a subscribed/contracted power level
    (kVA) separate from metered demand?

13. STRUCTURED DATA: Does this appear to be a Factur-X, ZUGFeRD,
    or similar structured invoice?
```

Updated complexity scoring for European invoices:

```python
def classify_complexity(signals, line_item_count, page_count, locale):
    score = 0
    # ...existing scoring...

    # European complexity additions
    if locale.country_code in EU_COUNTRIES:
        if 'multiple_vat_rates' in signals:
            score += 2  # Multi-rate VAT is inherently more complex
        if 'calorific_conversion' in signals:
            score += 1  # Extra validation needed
        if 'contracted_capacity_by_period' in signals:
            score += 2  # Spanish P1-P6 contracted capacity is complex
        if locale.country_code == 'FR' and signals.get('tou_convention') == 'TEMPO':
            score += 2  # French Tempo pricing has 6 tiers

    # Language penalty (non-English invoices are harder for current models)
    if locale.language not in ['en', 'de', 'fr', 'es', 'it']:
        score += 1  # Less common languages get a complexity bump

    return derive_tier(score)
```

---

## 5. Pass 1A/1B Changes — International Extraction Prompts

### 5.1 Additions to Pass 1A Prompt (Structure & Metering)

Add to the domain knowledge block:

```
INTERNATIONAL INVOICE AWARENESS:

NUMBER FORMATTING:
This invoice uses {locale.number_format} format.
- Decimal separator: "{locale.decimal_separator}"
- Thousands separator: "{locale.thousands_separator}"
- Example: "1.234,56" means one thousand two hundred thirty-four
  and fifty-six cents in this format.
ALWAYS parse numbers according to this convention.

DATE FORMATTING:
This invoice uses {locale.date_format} format.
- "05.03.2024" means {interpreted_date} in this locale.
When dates are ambiguous (both parts ≤ 12), flag them.

CURRENCY:
Currency is {locale.currency.code} ({locale.currency.symbol}).
Extract amounts with the exact string as printed for traceability.

EUROPEAN GAS METERING:
If this is a gas invoice, look for:
- Volume in m³ (cubic meters)
- Calorific value (Brennwert/PCS/CV) — a coefficient like 11.2 kWh/m³
- Volume correction factor (Zustandszahl/coefficient de correction)
- The conversion: m³ × correction × calorific value = kWh
- Extract ALL of these factors. They are essential for validation.

EUROPEAN IDENTIFIERS:
Look for and extract:
- POD / PDL / PDR / PCE / CUPS / EAN — delivery point identifiers
- Contract number (Vertragsnummer / Numéro de contrat)
- Customer VAT number and supplier VAT number
- Meter operator (if different from network operator)

CONTRACTED CAPACITY (European electricity):
Look for subscribed/contracted power:
- FR: "Puissance Souscrite" in kVA
- ES: "Potencia Contratada" in kW, possibly per-period (P1-P6)
- IT: "Potenza Impegnata" in kW
- DE: "Leistungspreis" component
This is NOT metered demand. It's a contractual maximum.
```

### 5.2 Additions to Pass 1B Prompt (Charges & Financial)

Add to the domain knowledge block:

```
VAT / TAX STRUCTURE (European invoices):

European invoices separate:
1. NET amount (before VAT) — "Netto" / "HT" (Hors Taxes) / "Imponible"
2. VAT amount — "MwSt" / "TVA" / "IVA" / "VAT"
3. GROSS amount (after VAT) — "Brutto" / "TTC" (Toutes Taxes Comprises) / "Total"

CRITICAL: Extract ALL THREE for each charge line where shown.
If the invoice groups charges by VAT rate, capture the grouping.

MULTIPLE VAT RATES:
One invoice may have charges at different VAT rates:
- Standard rate (19-22% depending on country)
- Reduced rate (5-10%)
- Zero rate (exempt or reverse charge)

Extract the VAT rate applicable to each charge or group of charges.

VAT SUMMARY TABLE:
European invoices often have a VAT summary table showing:
  Net Base | VAT Rate | VAT Amount
  450.00   | 19%      | 85.50
  25.00    | 7%       | 1.75
Extract this table in full.

REVERSE CHARGE:
If you see "Reverse Charge" / "Autoliquidation" / "Inversione contabile",
this means VAT = 0% and the buyer handles VAT. This is NOT an error.

ENERGY TAXES (separate from VAT):
These are per-unit taxes applied BEFORE VAT:
- DE: Stromsteuer (electricity tax), Erdgassteuer (gas tax)
- FR: CSPE, TCFE, CTA (electricity) / TICGN (gas)
- UK: CCL (Climate Change Levy)
- NL: Energiebelasting
These are NOT VAT. They are additional line items that VAT is applied ON TOP OF.

COUNTRY-SPECIFIC REGULATORY CHARGES:
{inject country-specific charge taxonomy based on locale.country_code}

TOU PERIOD NAMES:
- DE: HT (Hochtarif = peak), NT (Niedertarif = off-peak)
- FR: HP (Heures Pleines = peak), HC (Heures Creuses = off-peak),
      or Tempo: Bleu/Blanc/Rouge × HP/HC
- ES: P1 through P6 (P1 = most expensive)
- IT: F1 (peak), F2 (mid-peak), F3 (off-peak)
- UK: Often Day/Night or specific time bands

Map these to the standardized TOU representation.
```

### 5.3 Country-Specific Charge Taxonomies

These are injected into Pass 1B based on the detected country:

```python
CHARGE_TAXONOMIES = {
    "DE": {
        "energy_charges": [
            "Arbeitspreis HT/NT (energy charge peak/off-peak)",
            "Grundpreis/Leistungspreis (standing charge / capacity price)",
        ],
        "network_charges": [
            "Netzentgelt (network fee — may split into Arbeits- and Leistungspreis)",
            "Messstellenbetrieb (metering operation fee)",
            "Messung (metering charge)",
        ],
        "taxes_and_levies": [
            "Stromsteuer / Erdgassteuer (energy tax — per-kWh, pre-VAT)",
            "Konzessionsabgabe (concession fee — paid to municipality)",
            "§19 StromNEV-Umlage (grid fee surcharge)",
            "Offshore-Netzumlage (offshore grid levy)",
            "KWKG-Umlage (CHP levy)",
            "StromNEV §18 (avoided network costs)",
            "CO2-Abgabe (CO2 levy — gas only)",
            "Bilanzierungsumlage (gas balancing levy)",
        ],
        "vat": "Mehrwertsteuer (MwSt) — standard 19%, reduced 7%"
    },
    "FR": {
        "energy_charges": [
            "Abonnement (subscription / standing charge)",
            "Consommation HP/HC (consumption peak/off-peak)",
        ],
        "network_charges": [
            "TURPE (Tarif d'Utilisation des Réseaux Publics d'Électricité)",
            "Acheminement (delivery / transport)",
        ],
        "taxes_and_levies": [
            "CSPE (Contribution au Service Public de l'Électricité)",
            "TCFE (Taxes sur la Consommation Finale d'Électricité — dept + municipal)",
            "CTA (Contribution Tarifaire d'Acheminement — funds pension)",
            "TICGN (Taxe Intérieure de Consommation sur le Gaz Naturel — gas only)",
        ],
        "vat": "TVA — standard 20%, reduced 5.5% (on abonnement + CTA)"
    },
    "ES": {
        "energy_charges": [
            "Término de energía (energy charge) — per period P1-P6",
            "Término de potencia (capacity charge) — per period P1-P6",
        ],
        "network_charges": [
            "Peajes de acceso (access tolls)",
            "Cargos del sistema (system charges)",
        ],
        "taxes_and_levies": [
            "Impuesto eléctrico (electricity tax — 5.11269632%)",
            "Impuesto de hidrocarburos (hydrocarbon tax — gas)",
        ],
        "vat": "IVA — standard 21%, reduced 10% or 5% (temporary measures)"
    },
    "UK": {
        "energy_charges": [
            "Unit rate / Unit charge (p/kWh)",
            "Standing charge (p/day)",
        ],
        "network_charges": [
            "DUoS (Distribution Use of System)",
            "TNUoS (Transmission Network Use of System)",
            "BSUoS (Balancing Services Use of System)",
        ],
        "taxes_and_levies": [
            "CCL (Climate Change Levy — business consumers only)",
            "FiT levy (Feed-in Tariff levy)",
            "RO (Renewables Obligation)",
            "Capacity Market charge",
            "CFD (Contracts for Difference) levy",
        ],
        "vat": "VAT — standard 20%, reduced 5% (domestic energy)"
    },
    "IT": {
        "energy_charges": [
            "Spesa per la materia energia (energy cost)",
            "Quota energia / Quota fissa (energy component / fixed component)",
        ],
        "network_charges": [
            "Spesa per il trasporto e la gestione del contatore (transport + metering)",
            "Quota potenza (capacity component)",
        ],
        "taxes_and_levies": [
            "Spesa per oneri di sistema (system charges — renewable levies, etc.)",
            "Accisa (excise duty on energy)",
            "Addizionale regionale/comunale (regional/municipal surcharge)",
        ],
        "vat": "IVA — standard 22%, reduced 10% (domestic first home)"
    },
    "NL": {
        "energy_charges": [
            "Leveringstarief (supply rate)",
            "Vastrecht (standing charge)",
        ],
        "network_charges": [
            "Transportkosten (transport costs)",
            "Netbeheerkosten (network management costs)",
        ],
        "taxes_and_levies": [
            "Energiebelasting (energy tax — tiered, with tax reduction credit)",
            "ODE (Opslag Duurzame Energie — renewable surcharge)",
        ],
        "vat": "BTW — standard 21%"
    }
}
```

---

## 6. Pass 3 Changes — International Validation Rules

### 6.1 VAT Validation (new rule set)

```python
def validate_vat(extraction):
    """Validate European VAT structure."""
    results = []
    locale = extraction['extraction_metadata']['locale_context']

    if locale['tax_regime'] != 'eu_vat':
        return results  # Skip for non-EU invoices

    # Rule 1: Net + VAT = Gross for each charge line
    for charge in extraction['charges']:
        if charge.get('amount_net') and charge.get('vat_amount') and charge.get('amount_gross'):
            expected_gross = round(charge['amount_net']['value'] + charge['vat_amount']['value'], 2)
            stated_gross = charge['amount_gross']['value']
            if abs(expected_gross - stated_gross) > 0.02:
                results.append(VATError(
                    charge['line_id'],
                    f"Net ({charge['amount_net']['value']}) + VAT ({charge['vat_amount']['value']}) "
                    f"= {expected_gross}, but gross stated as {stated_gross}"
                ))

    # Rule 2: VAT amount = Net × VAT rate
    for charge in extraction['charges']:
        if charge.get('amount_net') and charge.get('vat_rate') and charge.get('vat_amount'):
            if charge['vat_category'] == 'reverse_charge':
                # VAT should be 0
                if charge['vat_amount']['value'] != 0:
                    results.append(VATError(charge['line_id'], "Reverse charge but VAT ≠ 0"))
                continue

            expected_vat = round(charge['amount_net']['value'] * charge['vat_rate'], 2)
            stated_vat = charge['vat_amount']['value']
            if abs(expected_vat - stated_vat) > 0.05:
                results.append(VATError(
                    charge['line_id'],
                    f"Net ({charge['amount_net']['value']}) × rate ({charge['vat_rate']}) "
                    f"= {expected_vat}, but VAT stated as {stated_vat}"
                ))

    # Rule 3: VAT summary table cross-check
    if extraction['totals'].get('vat_summary'):
        for vat_group in extraction['totals']['vat_summary']:
            # Sum all charges with this VAT rate
            matching_charges = [c for c in extraction['charges']
                               if c.get('vat_rate') == vat_group['vat_rate']]
            calculated_base = sum(c['amount_net']['value'] for c in matching_charges
                                 if c.get('amount_net'))
            stated_base = vat_group['taxable_base']['value']
            if abs(calculated_base - stated_base) > 0.50:
                results.append(VATError(
                    f"vat_summary_{vat_group['vat_rate']}",
                    f"Charges at {vat_group['vat_rate']*100}% sum to {calculated_base}, "
                    f"but VAT summary states base of {stated_base}"
                ))

    # Rule 4: Total net + total VAT = total gross
    if extraction['totals'].get('total_net') and extraction['totals'].get('total_vat'):
        expected = round(
            extraction['totals']['total_net']['value'] +
            extraction['totals']['total_vat']['value'], 2
        )
        stated = extraction['totals']['total_gross']['value']
        if abs(expected - stated) > 0.05:
            results.append(VATError("totals", f"Net + VAT = {expected}, gross = {stated}"))

    return results
```

### 6.2 Gas Calorific Value Validation (new rule set)

```python
def validate_gas_conversion(extraction):
    """Validate European gas volume-to-energy conversion."""
    results = []

    for meter in extraction['meters']:
        cf = meter.get('conversion_factors')
        if not cf:
            # US-style gas invoice — skip
            continue

        cv = cf.get('calorific_value', {}).get('value')
        vcf = cf.get('volume_correction_factor', {}).get('value', 1.0)
        volume = meter.get('consumption_volume', {}).get('raw_value')
        stated_energy = meter.get('consumption_energy', {}).get('value')

        if all([cv, volume, stated_energy]):
            calculated_energy = round(volume * vcf * cv, 1)
            if abs(calculated_energy - stated_energy) > 1:
                results.append(ConversionError(
                    meter['meter_number']['value'],
                    f"{volume} m³ × {vcf} × {cv} kWh/m³ = {calculated_energy} kWh, "
                    f"but invoice states {stated_energy} kWh"
                ))

        # Calorific value reasonableness
        if cv:
            if cv < 8 or cv > 14:
                results.append(ConversionWarning(
                    meter['meter_number']['value'],
                    f"Calorific value {cv} kWh/m³ is outside normal range (8-14)"
                ))

    return results
```

### 6.3 Contracted Capacity Validation (new rule set)

```python
def validate_contracted_capacity(extraction):
    """Validate European contracted capacity vs demand charges."""
    results = []

    for meter in extraction['meters']:
        cc = meter.get('contracted_capacity')
        if not cc:
            continue

        # If metered demand exceeds contracted capacity, there should be a penalty charge
        if meter.get('demand') and meter['demand']['value'] > cc['value']:
            penalty_charges = [c for c in extraction['charges']
                              if 'excess' in c['description']['value'].lower()
                              or 'exceso' in c['description']['value'].lower()
                              or 'dépassement' in c['description']['value'].lower()
                              or 'Überschreitung' in c['description']['value'].lower()]
            if not penalty_charges and not cc.get('exceeded'):
                results.append(CapacityWarning(
                    f"Demand ({meter['demand']['value']} {meter['demand']['unit']}) > "
                    f"contracted ({cc['value']} {cc['unit']}) but no excess penalty found"
                ))

    return results
```

### 6.4 Currency & Number Parsing Validation (new rule set)

```python
def validate_number_parsing(extraction):
    """
    Cross-check that number parsing was consistent.
    Look for contradictions that suggest wrong locale detection.
    """
    results = []
    locale = extraction['extraction_metadata']['locale_context']

    # Sanity: if total_amount_due is unreasonably large or small,
    # we may have parsed thousands separator as decimal
    total = extraction['totals']['total_amount_due']['value']
    if total > 1_000_000 or total < 0.01:
        results.append(ParsingWarning(
            "fatal",
            f"Total amount due ({total}) is extreme — possible number format misparse. "
            f"Detected format: {locale['number_format_detected']}"
        ))

    # Check: do all amounts use the same format?
    # If some have 2 decimal places and others have 3, something may be wrong
    for charge in extraction['charges']:
        original = charge['amount'].get('original_string', '')
        if original:
            # Count decimal places in original
            decimal_sep = locale['currency']['decimal_separator']
            if decimal_sep in original:
                decimal_part = original.split(decimal_sep)[-1]
                decimal_part = re.sub(r'[^\d]', '', decimal_part)  # Remove trailing symbols
                if len(decimal_part) not in [0, 2, 3, 4]:
                    results.append(ParsingWarning(
                        "non_fatal",
                        f"Unusual decimal places in '{original}' — verify parsing"
                    ))

    return results
```

### 6.5 Date Ambiguity Validation (new rule set)

```python
def validate_dates(extraction):
    """Flag ambiguous dates and check consistency."""
    results = []

    billing_start = extraction['invoice']['billing_period']['start']
    billing_end = extraction['invoice']['billing_period']['end']

    # If dates were flagged as ambiguous, check if the billing period makes sense
    if billing_start.get('ambiguous') or billing_end.get('ambiguous'):
        start = datetime.strptime(billing_start['value'], '%Y-%m-%d')
        end = datetime.strptime(billing_end['value'], '%Y-%m-%d')
        days = (end - start).days

        if days < 0:
            results.append(DateError(
                "fatal",
                f"Billing period is negative ({days} days). "
                f"Likely DD/MM vs MM/DD confusion. Start: {billing_start['original_string']}, "
                f"End: {billing_end['original_string']}"
            ))
        elif days > 400:
            results.append(DateError(
                "fatal",
                f"Billing period is {days} days. Likely date format misinterpretation."
            ))
        elif days > 95:
            results.append(DateWarning(
                "non_fatal",
                f"Billing period is {days} days — unusual but possible (quarterly/annual billing)."
            ))

    return results
```

---

## 7. Pass 4 Changes — International Audit Questions

Add conditional questions based on locale:

```python
def build_audit_questions(classification, locale):
    questions = BASE_QUESTIONS.copy()

    # ...existing conditional questions...

    # International questions
    if locale['tax_regime'] == 'eu_vat':
        questions.append(
            "Is VAT shown on this invoice? If so, what is the total net amount, "
            "the total VAT amount, and the total gross amount? "
            "Are there multiple VAT rates? If so, list each rate and its taxable base."
        )

    if locale['country_code'] == 'DE':
        questions.append(
            "Is a 'Stromsteuer' or 'Erdgassteuer' (energy tax) shown? What is the amount?"
        )

    if locale['country_code'] == 'FR':
        questions.append(
            "Are CSPE, TCFE, and CTA shown separately? What are their amounts?"
        )
        if classification['commodity_type'] == 'natural_gas':
            questions.append(
                "Is TICGN (gas tax) shown? What is the amount?"
            )

    if locale['country_code'] == 'UK':
        questions.append(
            "Is the Climate Change Levy (CCL) shown? Is there a CCL exemption "
            "(Levy Exemption Certificate / LEC / REGO)?"
        )

    if locale['country_code'] == 'ES':
        questions.append(
            "Are contracted power levels shown per period (P1-P6)? "
            "What are the values?"
        )

    if classification.get('has_calorific_conversion'):
        questions.append(
            "For gas: is a calorific value (CV / Brennwert / PCS) shown? "
            "What is the value? Is a volume correction factor also shown?"
        )

    if locale['currency']['decimal_separator'] == ',':
        questions.append(
            "Confirm: is the total amount due closer to {option_a} or {option_b}? "
            "(This verifies number format interpretation.)"
            # option_a = value parsed as comma-decimal
            # option_b = value parsed as dot-decimal
        )

    return questions
```

---

## 8. Rounding Rules by Jurisdiction

European countries have different legal requirements for rounding:

```python
ROUNDING_RULES = {
    "DE": {
        "line_item_rounding": 2,       # Round to 2 decimal places
        "vat_rounding": "per_line",    # VAT calculated per line, then summed
        "tolerance": 0.02,             # Accept ≤ €0.02 variance
    },
    "FR": {
        "line_item_rounding": 2,
        "vat_rounding": "on_total",    # VAT calculated on sum of net amounts
        "tolerance": 0.05,             # French invoices frequently have small rounding
    },
    "ES": {
        "line_item_rounding": 2,       # But electricity tax uses 8 decimal rate
        "vat_rounding": "per_line",
        "tolerance": 0.05,
        "special": "Electricity tax rate is 5.11269632% — expect unusual decimal results"
    },
    "UK": {
        "line_item_rounding": 2,       # But unit rates often in p/kWh with 4+ decimals
        "vat_rounding": "on_total",
        "tolerance": 0.01,             # UK is generally precise
        "special": "Standing charges in p/day — multiply by days, then convert to £"
    },
    "IT": {
        "line_item_rounding": 2,
        "vat_rounding": "per_line",
        "tolerance": 0.10,             # Italian utility invoices frequently have small variances
    },
    "NL": {
        "line_item_rounding": 2,
        "vat_rounding": "on_total",
        "tolerance": 0.02,
        "special": "Energiebelasting has a tax reduction credit (belastingvermindering) that offsets part of the energy tax. This is a CREDIT, not an error."
    },
    "US": {
        "line_item_rounding": 2,
        "vat_rounding": None,          # No VAT
        "tolerance": 0.05,
    },
    "MX": {
        "line_item_rounding": 2,
        "vat_rounding": "on_total",    # IVA at 16%
        "tolerance": 0.05,
        "special": "CFDI (Comprobante Fiscal Digital) — invoices are digitally signed XML. Extract UUID for traceability."
    }
}

def get_rounding_tolerance(locale, charge_category):
    """Get acceptable rounding tolerance for this jurisdiction."""
    rules = ROUNDING_RULES.get(locale['country_code'], ROUNDING_RULES['US'])
    base_tolerance = rules['tolerance']

    # Tax calculations may have higher tolerance due to rate precision
    if charge_category in ['tax', 'rider'] and rules.get('special'):
        return base_tolerance * 2

    return base_tolerance
```

---

## 9. Unit Normalization — International

```python
UNIT_CONVERSIONS = {
    # Gas
    "m³_to_kWh": lambda m3, cv, vcf=1.0: m3 * vcf * cv,  # Requires calorific value
    "therms_to_kWh": lambda therms: therms * 29.3071,
    "CCF_to_therms": lambda ccf: ccf * 1.037,
    "MCF_to_therms": lambda mcf: mcf * 10.37,
    "dekatherms_to_kWh": lambda dt: dt * 293.071,
    "MJ_to_kWh": lambda mj: mj / 3.6,
    "GJ_to_kWh": lambda gj: gj * 277.778,

    # Electric
    "MWh_to_kWh": lambda mwh: mwh * 1000,
    "kWh_to_kWh": lambda kwh: kwh,  # Identity

    # Water
    "m³_to_gallons": lambda m3: m3 * 264.172,
    "gallons_to_m³": lambda gal: gal / 264.172,
    "CCF_water_to_m³": lambda ccf: ccf * 2.8317,
    "liters_to_m³": lambda l: l / 1000,
}

# Canonical units per commodity per market
CANONICAL_UNITS = {
    "electricity": {"energy": "kWh", "demand": "kW"},
    "natural_gas": {
        "us": {"energy": "therms"},
        "eu": {"energy": "kWh", "volume": "m³"},
    },
    "water": {
        "us": {"volume": "gallons"},
        "eu": {"volume": "m³"},
    }
}
```

---

## 10. Mexican Market Additions (LATAM)

Since you're based in Reynosa, adding CFE (Comisión Federal de Electricidad) and Mexican market specifics:

| Concept | Detail | Extraction Impact |
|---|---|---|
| **CFE Tariffs** | PDBT, GDMTH, GDMTO, DIST, DIT, HM, HS, etc. Complex tariff structure. | Must extract tariff code. |
| **DAC (Doméstica de Alto Consumo)** | Residential penalty tariff for exceeding subsidized consumption threshold. | Must detect DAC vs. normal residential. |
| **CFDI** | All Mexican invoices are digitally signed XML (Comprobante Fiscal Digital por Internet). UUID is the legal identifier. | Extract UUID. If XML is available, use it as primary source. |
| **IVA** | 16% standard VAT. Shown as separate line. | Validate: net × 1.16 ≈ total. |
| **Factor de Potencia** | Power factor penalty is very strictly enforced. Below 0.9 = surcharge, above 0.9 = bonus/credit. | Must capture power factor value and whether it's a bonus or penalty. |
| **Cargo por Demanda** | Demand charge, measured. | Standard demand charge handling. |
| **Cargo por Energía** | Energy charges, often with base/intermediate/peak periods. | TOU-like structure. |
| **DAP (Derecho de Alumbrado Público)** | Municipal street lighting charge added to electricity bills. | Fixed charge, non-energy. |
| **Number format** | Mexico uses `$1,234.56` (same as US) but currency is MXN. | Detect MXN vs USD based on invoice context. |

---

## 11. Updated Confidence Scoring — International Factors

Add to the confidence scoring algorithm:

```python
def compute_confidence_international(extraction, validation, audit, locale):
    score = compute_confidence(extraction, validation, audit)  # Base scoring

    # Number format confidence
    if locale.get('number_format_confidence', 1.0) < 0.7:
        score -= 0.10  # Uncertain number parsing is a significant risk

    # Ambiguous dates
    ambiguous_dates = count_ambiguous_dates(extraction)
    if ambiguous_dates > 0:
        score -= 0.05 * ambiguous_dates

    # VAT validation failures
    vat_errors = [e for e in validation.get('vat_errors', []) if not e.is_rounding]
    score -= 0.12 * len(vat_errors)  # VAT errors are high-impact

    # Calorific conversion mismatch
    conversion_errors = validation.get('conversion_errors', [])
    score -= 0.15 * len(conversion_errors)  # Fatal for gas invoices

    # Non-English, non-major language
    if locale['language'] not in ['en', 'de', 'fr', 'es', 'it', 'nl', 'pt']:
        score -= 0.05  # Less model confidence for uncommon languages

    # Structured invoice data available (BONUS — increases confidence)
    if extraction['classification'].get('has_structured_invoice_data'):
        score += 0.10  # Machine-readable source data = higher trust

    return max(score, 0.0)
```

---

## 12. Summary of All Schema Changes

For quick reference — fields added or modified from v2:

| Schema Location | Change | Reason |
|---|---|---|
| `extraction_metadata.locale_context` | **NEW** — country, language, currency, number format, date format, tax regime | Drives all international parsing |
| Every `amount` field | Added `currency`, `original_string` | Multi-currency + traceability |
| Each charge line | Added `amount_net`, `vat_rate`, `vat_amount`, `amount_gross`, `vat_category`, `tax_calculation_order` | European VAT structure |
| `totals` | Added `vat_summary[]`, `total_net`, `total_vat`, `total_gross`, `reverse_charge_applied`, `vat_numbers` | VAT reconciliation |
| `meters` (gas) | Added `consumption_volume`, `conversion_factors` (calorific value, correction factor, formula), `consumption_energy` | European gas billing |
| `meters` (electricity) | Added `contracted_capacity`, `contracted_capacity_by_period[]` | European capacity subscriptions |
| `account` | Added `contract_number`, `customer_vat_number`, `pod_pdr`, `ean_code`, `network_operator`, `metering_operator` | European market identifiers |
| `classification` | Added `market_model`, `country_code`, `has_vat_structure`, `has_reverse_charge`, `has_calorific_conversion`, `has_contracted_capacity`, `has_multiple_vat_rates`, `has_structured_invoice_data`, `tou_naming_convention` | International routing |
| `validation` | Added `vat_results`, `conversion_results`, `date_ambiguity_results`, `number_parsing_results` | International validation rules |
