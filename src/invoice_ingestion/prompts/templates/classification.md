# Invoice Classification

You are an expert energy utility invoice analyst. Examine this utility invoice and classify it.

Answer ALL of the following questions:

## 1. COMMODITY
What type of utility service is this invoice for?
- natural_gas
- electricity
- water
- multi_commodity (if multiple services on one invoice)

## 2. MARKET TYPE
- regulated (single utility handles everything)
- deregulated (separate supplier and utility)
- unknown

## 3. COMPLEXITY SIGNALS
Check ALL that apply:
- multi_meter: more than one meter on this invoice
- tou_present: time-of-use rate tiers visible
- demand_charges: kW or kVA demand charges present
- net_metering: solar/generation credits shown
- supplier_split: separate supplier vs utility charges
- prior_period_adjustments: corrections to previous billing periods
- budget_billing: levelized payment plan
- tiered_rates: block/tier consumption pricing
- estimated_reads: estimated meter reads (flagged with E or EST)
- multi_page_charges: charge tables span 3+ pages

## 4. INTERNATIONAL SIGNALS (if applicable)
- country: What country is this invoice from? (ISO 2-letter code or "unknown")
- number_format: How are numbers formatted? ("1.234,56" for EU or "1,234.56" for US)
- has_vat: Is there a VAT/TVA/IVA/MwSt section? (true/false)
- has_multiple_vat_rates: Are multiple VAT rates applied? (true/false)
- has_calorific_conversion: For gas, is there a calorific value / Brennwert / PCS shown? (true/false)
- has_contracted_capacity: Is there contracted power / puissance souscrite? (true/false)
- has_structured_data: Does this appear to be a Factur-X/ZUGFeRD/FatturaPA invoice? (true/false)
- date_format: What date format is used? ("DD/MM/YYYY", "MM/DD/YYYY", "DD.MM.YYYY", "YYYY-MM-DD")

## 5. ESTIMATED LINE ITEM COUNT
Approximate number of individual charge lines visible.

## 6. LANGUAGE
Primary language of the invoice (ISO 639-1 code, e.g., "en", "de", "fr", "es").

## 7. FORMAT RECOGNITION
Does this look like a known utility template? If recognizable, provide the utility name. Otherwise respond "unknown".

{domain_knowledge}

{few_shot_context}

Respond as JSON:
```json
{
  "commodity_type": "...",
  "commodity_confidence": 0.0-1.0,
  "market_type": "...",
  "complexity_signals": ["..."],
  "estimated_line_item_count": 0,
  "language": "...",
  "format_fingerprint": "...",
  "country_code": "...",
  "number_format": "...",
  "date_format": "...",
  "has_vat": false,
  "has_multiple_vat_rates": false,
  "has_calorific_conversion": false,
  "has_contracted_capacity": false,
  "has_structured_data": false
}
```