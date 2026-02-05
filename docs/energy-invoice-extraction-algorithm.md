# Energy Commodity Invoice Extraction — Algorithm & Architecture v2

## Revision Notes from v1

| v1 Issue | v2 Change |
|---|---|
| "Determinism" was oversold | Reframed as **bounded-variance, auditable extraction**. Output drift is a first-class event, not an anomaly. |
| Pass 1 did too much in one shot | Split into **Pass 1A** (header/account/meters) and **Pass 1B** (charges/tables/riders). Same images, different prompts. |
| Confidence scoring was linear and hand-tuned | Replaced with **weighted, tiered scoring** with fatal vs. non-fatal dimensions. |
| Audit questions were too shallow | Made **conditional on commodity + complexity tier**. Deeper questions for high-risk invoices. |
| No pre-classification gate | Added **Pass 0.5: Classification & Routing** before extraction. |
| Missing temporal attribution | Added `charge_period` with `attribution_type` to every charge line. |
| Assumed clean billing math | Introduced **billing math vs. utility math** separation with `utility_adjustment_detected` handling. |
| Generic tech stack | Reoriented to **Azure-first** architecture. |
| Heavy UI assumption | Scoped UI to **minimal correction interface only**. |

---

## 1. The Problem Space: Energy Invoice Complexity

### 1.1 Natural Gas Invoices — Key Concepts

| Concept | What It Means | Why Extraction Cares |
|---|---|---|
| **Commodity vs. Delivery** | Gas itself (commodity) is often billed separately from pipeline transport (delivery/distribution). You may have two different suppliers on one invoice. | Must split and attribute charges correctly. |
| **Therms / CCF / MCF / Dekatherms** | Different unit measures. 1 CCF ≈ 1.037 therms. MCF = 1,000 cubic feet. Dekatherm = 10 therms. | Must normalize to a common unit. |
| **Demand Charges** | Charged based on peak usage (highest single-hour/day consumption) in the billing period, not total volume. | This is NOT a per-unit charge — must be extracted as a separate line. |
| **Balancing / Cashout Charges** | When actual consumption differs from nominated/scheduled volume, imbalance penalties apply. | Appears irregularly; easy to miss. |
| **Gas Cost Adjustment (GCA)** | A variable rider that adjusts for upstream gas price fluctuations. Can be positive or negative. | Can appear as a credit. Extraction must handle negative values. |
| **Minimum / Take-or-Pay** | Contract-guaranteed minimum volume. Customer pays even if they use less. | Invoice may show "billed volume" ≠ "actual volume." |
| **Transportation Tiers** | Pipeline transport may be tiered (first X therms at rate A, next Y at rate B). | Must capture tier breakdowns, not just totals. |
| **Weather Normalization / HDD** | Some invoices show Heating Degree Days or weather normalization factors that affect pricing or comparisons. | Useful metadata for analytics; shouldn't be confused with charges. |
| **Capacity Assignment / Reservation** | Pipeline capacity reserved for the customer, billed as a fixed demand-like charge regardless of usage. | Fixed charge that doesn't correlate with consumption. |

### 1.2 Electricity Invoices — Key Concepts

| Concept | What It Means | Why Extraction Cares |
|---|---|---|
| **Supply vs. Distribution** | Deregulated markets separate the electricity supplier (competitive) from the utility (distribution, T&D). One account may have two invoices or a consolidated one. | Must tag each charge to "supply" or "distribution." |
| **Demand Charges (kW)** | Based on peak 15-min or 30-min demand interval. Billed in $/kW. Completely different from energy (kWh) charges. | kW ≠ kWh. These are different line items. |
| **Time-of-Use (TOU) Rates** | Pricing varies by time block (on-peak, off-peak, shoulder/mid-peak, super-off-peak). | Must capture each TOU tier and its rate + volume separately. |
| **Net Metering** | Customer generates (solar, etc.) and exports surplus to grid. Invoice shows import, export, and net. Credits may roll over. | Must capture generation, export, import, net consumption, and any credit balance. |
| **Power Factor Penalties** | If reactive power (kVAR) is too high relative to real power (kW), a penalty or surcharge applies. | Appears as an adjustment; easy to misclassify. |
| **Capacity / Transmission Tags (ICAP, PLC)** | ICAP (Installed Capacity), TCAP, transmission charges — often tagged to peak load contribution (PLC) from a historical period, sometimes 12+ months prior. | These are pass-through charges with unique calculation logic and **temporal misalignment** — the charge period ≠ the billing period. |
| **Riders / Surcharges** | Renewable energy surcharges, infrastructure modernization, storm recovery, nuclear decommissioning, etc. | Can be 10+ separate line items. Must capture all. Some apply to subsets of other charges, not to total consumption. |
| **Rate Schedule / Tariff Code** | e.g., "SC-9 Rate II" or "GS-TOU-3". Determines all applicable rates. | Critical metadata for validation and rate comparison. |
| **Reactive Demand (kVAR / kVA)** | Some tariffs bill on apparent power (kVA) rather than real power (kW), or add a reactive component. | Must capture the correct demand unit and any power factor adjustment. |
| **Coincident vs. Non-Coincident Demand** | Peak demand measured at the system peak (coincident) vs. the customer's own peak (non-coincident). Different charges may apply to each. | Must differentiate which demand value drives which charge. |

### 1.3 Water Invoices — Key Concepts

| Concept | What It Means | Why Extraction Cares |
|---|---|---|
| **Water + Sewer** | Almost always billed together but are separate services with separate rates. | Must split charges between water and sewer. |
| **Tiered / Block Rates** | Increasing price per unit at higher consumption (conservation pricing). | Must capture each tier: threshold, volume, rate. |
| **Base / Service Charge** | Fixed monthly fee based on meter size (e.g., 5/8" vs. 2" meter). | Not based on consumption — separate line item. |
| **Stormwater / Drainage** | Fixed fee based on impervious surface area of property, not water usage. | Completely decoupled from metering data. |
| **Units: Gallons / CCF / Cubic Meters** | 1 CCF = 748 gallons. Some use cubic meters. | Must normalize. |
| **Estimated vs. Actual Reads** | If meter couldn't be read, estimate is used. Often flagged with "E" or "EST." | Must capture read type — affects data confidence. |
| **Sewer Cap / Winter Average** | Some jurisdictions cap sewer volume at the winter average water usage (assumption: summer excess is irrigation, not sewer). | Sewer billed volume may differ from water billed volume. |

### 1.4 Cross-Commodity Concepts

| Concept | Applies To | Detail |
|---|---|---|
| **Fixed Fees** | All | Customer charges, minimum bills, meter fees — independent of consumption. |
| **Taxes & Assessments** | All | Sales tax, utility tax, franchise fees, gross receipts tax — jurisdiction-dependent. Some taxes apply only to subsets of charges. |
| **Late Fees / Penalties** | All | Past-due charges carried forward. |
| **Budget Billing** | All | Levelized monthly payment vs. actual cost. Invoice may show both actual and budget amounts. |
| **Multi-Meter Accounts** | All | Single invoice covering multiple meters/service points. Each has its own consumption. |
| **Billing Determinants** | All | The raw inputs that drive charges: read dates, meter multipliers, loss factors, etc. |
| **Previous Balance / Payments** | All | Running account balance. Important for reconciliation but NOT current-period charges. |
| **Prior Period Adjustments** | All | Corrections to previous invoices appearing on the current one. These reference a different billing period than the invoice date. |
| **Proration** | All | Partial-period charges when service starts/stops mid-cycle, or rate changes mid-cycle. Two rate sets may appear on one invoice. |
| **Minimum Bill** | All | If consumption-based charges fall below a threshold, the utility bills the minimum instead. Stated charges may not reconcile via quantity × rate. |

---

## 2. Common Output Schema

### 2.1 Design Principles

- Every extracted value carries its own `confidence` score (0.0–1.0).
- Every extracted value carries `source_location` for traceability.
- Every charge carries `charge_period` for temporal attribution.
- Math validation distinguishes **expected math** from **stated math** from **utility-adjusted math**.
- Nullable fields are explicit nulls, never omitted.

### 2.2 Schema

```json
{
  "extraction_metadata": {
    "extraction_id": "uuid",
    "extraction_timestamp": "ISO-8601",
    "pipeline_version": "v2.1.0",
    "models_used": {
      "classification": { "model": "claude-haiku-4-5-20251001", "temperature": 0.0 },
      "extraction_1a": { "model": "claude-sonnet-4-20250514", "temperature": 0.0 },
      "extraction_1b": { "model": "claude-sonnet-4-20250514", "temperature": 0.0 },
      "schema_mapping": { "model": "claude-haiku-4-5-20251001", "temperature": 0.0 },
      "audit": { "model": "gpt-4o-2024-11-20", "temperature": 0.0 }
    },
    "prompt_versions": {
      "classification": "v1.2.0",
      "extraction_1a": "v2.3.1",
      "extraction_1b": "v2.3.1",
      "schema_mapping": "v1.5.0",
      "audit": "v1.4.0"
    },
    "few_shot_context_hash": "sha256 of injected examples (null if none)",
    "overall_confidence": 0.0-1.0,
    "confidence_tier": "auto_accept | targeted_review | full_review",
    "flags": [],
    "processing_time_ms": 1234,
    "source_document": {
      "file_hash": "sha256",
      "file_type": "pdf | image",
      "page_count": 3,
      "pages_used": [1, 2, 3],
      "pages_discarded": [],
      "ocr_applied": true,
      "image_quality_score": 0.0-1.0,
      "language_detected": "es",
      "language_translated": true
    }
  },

  "classification": {
    "commodity_type": "natural_gas | electricity | water | multi_commodity",
    "commodity_confidence": 0.98,
    "complexity_tier": "simple | standard | complex | pathological",
    "complexity_signals": ["multi_meter", "tou_present", "net_metering"],
    "market_type": "regulated | deregulated | unknown",
    "has_supplier_split": true,
    "has_demand_charges": true,
    "has_tou": true,
    "has_net_metering": false,
    "has_prior_period_adjustments": false,
    "estimated_line_item_count": 24,
    "format_fingerprint": "coned-commercial-2024-v2 | unknown"
  },

  "invoice": {
    "invoice_number": { "value": "123456", "confidence": 0.99, "source_location": "page1:top-right" },
    "invoice_date": { "value": "2024-11-15", "confidence": 0.98, "source_location": "page1:header" },
    "due_date": { "value": "2024-12-05", "confidence": 0.95, "source_location": "page1:header" },
    "billing_period": {
      "start": { "value": "2024-10-15", "confidence": 0.97 },
      "end": { "value": "2024-11-14", "confidence": 0.97 },
      "days": 31
    },
    "rate_schedule": { "value": "GS-TOU-3", "confidence": 0.88, "source_location": "page1:mid-left" },
    "statement_type": "regular | final | estimated | corrected | credit_memo"
  },

  "account": {
    "account_number": { "value": "...", "confidence": 0.99, "source_location": "page1:header" },
    "customer_name": { "value": "...", "confidence": 0.97, "source_location": "page1:header" },
    "service_address": { "value": "...", "confidence": 0.95, "source_location": "page1:header" },
    "billing_address": { "value": "...", "confidence": 0.90, "source_location": "page1:header" },
    "utility_provider": { "value": "ConEdison", "confidence": 0.99, "source_location": "page1:logo" },
    "supplier": { "value": "Direct Energy", "confidence": 0.92, "source_location": "page2:supply-section", "note": "Competitive supplier" }
  },

  "meters": [
    {
      "meter_number": { "value": "M-001", "confidence": 0.96, "source_location": "page2:meter-table" },
      "service_point_id": null,
      "read_type": "actual | estimated | customer",
      "read_date_start": "2024-10-15",
      "read_date_end": "2024-11-14",
      "previous_read": 45230,
      "current_read": 45980,
      "multiplier": { "value": 10.0, "confidence": 0.90, "source_location": "page2:meter-table:footnote" },
      "loss_factor": null,
      "consumption": {
        "raw_value": 750,
        "raw_unit": "CCF",
        "normalized_value": 777.75,
        "normalized_unit": "therms",
        "normalization_formula": "750 CCF × 1.037 = 777.75 therms"
      },
      "demand": {
        "value": 45.2,
        "unit": "kW",
        "demand_type": "non_coincident | coincident | reactive",
        "peak_datetime": "2024-10-28T14:30:00",
        "source_location": "page2:demand-section"
      },
      "generation": null,
      "net_consumption": null,
      "tou_breakdown": [
        {
          "period": "on-peak",
          "consumption": { "value": 280, "unit": "kWh" },
          "demand": { "value": 45.2, "unit": "kW" }
        },
        {
          "period": "off-peak",
          "consumption": { "value": 470, "unit": "kWh" },
          "demand": null
        }
      ]
    }
  ],

  "charges": [
    {
      "line_id": "L001",
      "description": { "value": "Energy Charge - On Peak", "confidence": 0.94, "source_location": "page2:line4" },
      "category": "energy | demand | fixed | rider | tax | penalty | credit | adjustment | minimum | other",
      "subcategory": "on_peak_energy",
      "charge_owner": "utility | supplier | government | other",
      "charge_section": "supply | distribution | taxes | other",
      "quantity": { "value": 280, "unit": "kWh" },
      "rate": { "value": 0.0845, "unit": "$/kWh" },
      "amount": { "value": 23.66, "confidence": 0.96, "source_location": "page2:line4:col-amount" },
      "charge_period": {
        "start": "2024-10-15",
        "end": "2024-11-14",
        "attribution_type": "current | prior_period | rolling_average | estimated | prorated",
        "reference_period_note": null
      },
      "applies_to_meter": "M-001",
      "math_check": {
        "expected_amount": 23.66,
        "calculation": "280 × 0.0845 = 23.66",
        "matches_stated": true,
        "variance": 0.00,
        "utility_adjustment_detected": false,
        "adjustment_note": null
      }
    }
  ],

  "totals": {
    "supply_subtotal": { "value": 98.20, "confidence": 0.97, "source_location": "page2:supply-total" },
    "distribution_subtotal": { "value": 67.15, "confidence": 0.96, "source_location": "page2:dist-total" },
    "taxes_subtotal": { "value": 22.10, "confidence": 0.97, "source_location": "page3:tax-total" },
    "current_charges": { "value": 187.45, "confidence": 0.98, "source_location": "page1:summary-box" },
    "previous_balance": { "value": 0.00, "confidence": 0.99, "source_location": "page1:balance-section" },
    "payments_received": { "value": -145.20, "confidence": 0.97, "source_location": "page1:payment-line" },
    "late_fees": { "value": 0.00, "confidence": 0.99 },
    "total_amount_due": { "value": 187.45, "confidence": 0.99, "source_location": "page1:amount-due-box" },
    "budget_billing_amount": null,
    "minimum_bill_applied": false
  },

  "validation": {
    "math_results": {
      "line_items_sum": 187.45,
      "stated_current_charges": 187.45,
      "difference": 0.00,
      "line_items_sum_valid": true,
      "section_subtotals_valid": true,
      "account_balance_valid": true,
      "notes": []
    },
    "utility_math_adjustments": [
      {
        "description": "Rider XYZ rounds to nearest cent differently than simple multiplication",
        "expected_by_multiplication": 4.537,
        "stated_on_invoice": 4.54,
        "variance": 0.003,
        "disposition": "accepted_utility_rounding"
      }
    ],
    "consumption_crosschecks": {
      "meter_reads_match_consumption": true,
      "tou_sums_to_total": true,
      "net_metering_balance_valid": null,
      "notes": []
    },
    "logic_checks": {
      "commodity_unit_consistency": true,
      "billing_period_reasonable": true,
      "negative_amounts_on_credits_only": true,
      "demand_present_if_expected": true,
      "notes": []
    },
    "audit_results": {
      "fields_checked": 8,
      "fields_matched": 8,
      "fields_mismatched": 0,
      "mismatches": [],
      "audit_model": "gpt-4o-2024-11-20"
    },
    "overall_math_disposition": "clean | rounding_variance_only | discrepancy_found | minimum_bill_detected"
  },

  "traceability": [
    {
      "field": "charges[0].amount",
      "value": 23.66,
      "reasoning": "280 kWh × $0.0845/kWh = $23.66. Matches line item on page 2, column 'Amount'.",
      "source_pages": [2],
      "extraction_pass": "1b",
      "validated_by": ["pass3:rate_multiplication", "pass4:audit_crosscheck"],
      "human_reviewed": false,
      "confidence_factors": ["clear_text", "math_verified", "audit_confirmed"]
    }
  ],

  "bounded_variance_record": {
    "is_reprocessing": false,
    "previous_extraction_id": null,
    "drift_detected": false,
    "drift_fields": [],
    "drift_disposition": null
  }
}
```

---

## 3. The Extraction Pipeline — Multi-Pass Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        INVOICE INPUT (PDF / Image)                           │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │   PASS 0: INGESTION     │
                     │   File normalization,   │
                     │   image prep, language   │
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │   PASS 0.5: CLASSIFY    │
                     │   Commodity, complexity, │
                     │   routing decision       │
                     └────────────┬────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                ┌───▼───┐   ┌────▼────┐   ┌────▼────┐
                │SIMPLE │   │STANDARD │   │COMPLEX/ │
                │ ROUTE │   │  ROUTE  │   │PATHOLOG.│
                └───┬───┘   └────┬────┘   └────┬────┘
                    │            │              │
                    └─────────┬──┘     ┌────────▼────────┐
                              │        │ PRE-FLAG FOR    │
                              │        │ HUMAN REVIEW    │
                              │        └────────┬────────┘
                              │                 │
                    ┌─────────▼─────────────────▼──┐
                    │   PASS 1A: VISION EXTRACT     │
                    │   Headers, Account, Meters,   │
                    │   Periods, Rate Schedule       │
                    └─────────────┬─────────────────┘
                                  │
                    ┌─────────────▼─────────────────┐
                    │   PASS 1B: VISION EXTRACT     │
                    │   Charges, Tables, TOU,       │
                    │   Riders, Taxes, Totals        │
                    └─────────────┬─────────────────┘
                                  │
                    ┌─────────────▼─────────────────┐
                    │   PASS 2: SCHEMA MAPPING      │
                    │   Normalize, classify,         │
                    │   temporal attribution          │
                    └─────────────┬─────────────────┘
                                  │
                    ┌─────────────▼─────────────────┐
                    │   PASS 3: VALIDATION          │
                    │   Expected math vs stated math │
                    │   Utility adjustment detection │
                    │   Logic checks                 │
                    └─────────────┬─────────────────┘
                                  │
                    ┌─────────────▼─────────────────┐
                    │   PASS 4: AUDIT               │
                    │   Conditional questions        │
                    │   based on classification      │
                    └─────────────┬─────────────────┘
                                  │
                    ┌─────────────▼─────────────────┐
                    │   CONFIDENCE GATE             │
                    │   Weighted, tiered scoring     │
                    └──────┬──────────┬─────────────┘
                           │          │
                  ┌────────▼┐   ┌─────▼───────────┐
                  │  AUTO   │   │  HUMAN REVIEW   │
                  │ ACCEPT  │   │  (targeted or   │
                  │         │   │   full)          │
                  └────┬────┘   └────┬────────────┘
                       │             │
                       │    ┌────────▼────────┐
                       │    │  CORRECTIONS →  │
                       │    │  FEEDBACK STORE  │
                       │    └────────┬────────┘
                       │             │
                  ┌────▼─────────────▼────┐
                  │    FINAL OUTPUT        │
                  │    (Structured JSON)   │
                  └───────────────────────┘
```

---

## 4. Pass-by-Pass Detail

### Pass 0: Ingestion & Pre-Processing

**Purpose:** Normalize the input into a consistent format the LLM can consume reliably.

**Steps:**

1. **File Identification**
   - Detect file type (PDF, PNG, JPG, TIFF, HEIC).
   - Compute SHA-256 hash for deduplication and traceability.
   - Check for duplicate submissions (same hash = already processed → return cached result or flag for re-extraction).

2. **PDF Processing**
   - Attempt native text extraction (PyMuPDF / pdfplumber).
   - If text layer is present AND readable → flag as `text_pdf`.
   - If text layer is absent or garbled → flag as `image_pdf`, proceed to OCR path.
   - For `text_pdf`: extract text AND render pages as images (you'll use both).
   - Render at consistent DPI (300 DPI) to minimize pixel-level variance across re-runs.

3. **Image Normalization** (for image-based inputs)
   - Deskew (auto-rotate to straight alignment).
   - Contrast normalization.
   - Resolution upscaling if below 200 DPI (bicubic).
   - **Determinism note:** Store the normalized image and its hash. On re-runs, compare normalized image hashes. If they drift due to preprocessing changes, log as a `preprocessing_drift` event. Consider pinning preprocessing library versions.
   - For multi-page: split into individual page images.

4. **Language Detection**
   - Run text (extracted or OCR'd) through a language detector (e.g., Azure AI Language or a simple library like `langdetect`).
   - If non-English: flag for translation in Pass 1.
   - Store original language text alongside translation.

5. **Image Quality Scoring**
   - Compute a quality score (resolution, contrast, blur detection).
   - Below threshold → flag as `low_quality_source` (affects confidence downstream).

**Output:**
```json
{
  "ingestion_id": "uuid",
  "file_hash": "sha256",
  "normalized_image_hash": "sha256 (of rendered/enhanced images)",
  "image_quality_score": 0.85,
  "pages": [
    {
      "page_number": 1,
      "image_base64": "...",
      "extracted_text": "..." or null,
      "language": "en",
      "quality_score": 0.90
    }
  ]
}
```

---

### Pass 0.5: Classification & Routing (NEW)

**Purpose:** Before the expensive extraction passes, understand what you're dealing with and route accordingly.

**Model:** Cheap/fast model (Claude Haiku 4.5). Vision input — send page 1 (summary page) and a random detail page.

**Prompt:**
```
Examine this utility invoice and classify it:

1. COMMODITY: natural_gas | electricity | water | sewer | multi_commodity
2. MARKET TYPE: regulated | deregulated | unknown
3. COMPLEXITY SIGNALS (check all that apply):
   - multi_meter (more than one meter on this invoice)
   - tou_present (time-of-use rate tiers)
   - demand_charges (kW or kVA charges)
   - net_metering (solar/generation credits)
   - supplier_split (separate supplier vs utility charges)
   - prior_period_adjustments (corrections to previous periods)
   - budget_billing (levelized payment plan)
   - tiered_rates (block/tier consumption pricing)
   - estimated_reads (estimated meter reads)
   - multi_page_charges (charge tables span 3+ pages)
4. ESTIMATED LINE ITEM COUNT: approximate number of charge lines
5. LANGUAGE: primary language of the invoice
6. FORMAT MATCH: does this look like a known utility template?
   Respond with utility name if recognizable, or "unknown"
```

**Complexity Tier Derivation (Code):**
```python
def classify_complexity(signals, line_item_count, page_count):
    score = 0
    high_complexity_signals = {'multi_meter', 'net_metering', 'prior_period_adjustments', 'multi_page_charges'}
    medium_complexity_signals = {'tou_present', 'demand_charges', 'supplier_split', 'tiered_rates'}

    for s in signals:
        if s in high_complexity_signals:
            score += 3
        elif s in medium_complexity_signals:
            score += 1

    if line_item_count > 30:
        score += 3
    elif line_item_count > 15:
        score += 1

    if page_count > 5:
        score += 2

    if score <= 2:
        return "simple"      # Single commodity, few lines, standard format
    elif score <= 6:
        return "standard"    # Most commercial invoices
    elif score <= 10:
        return "complex"     # Multi-meter, TOU, demand, etc.
    else:
        return "pathological" # Pre-flag for human review
```

**Routing Rules:**

| Tier | Extraction Strategy | Human Review Default |
|---|---|---|
| Simple | Standard Pass 1A + 1B | Auto-accept if confidence ≥ 0.95 |
| Standard | Standard Pass 1A + 1B, full audit | Auto-accept if confidence ≥ 0.93 |
| Complex | Standard extraction + expanded audit questions | Targeted review always |
| Pathological | Standard extraction + flag entire invoice for full human review | Full review always |

**Why this matters:** You're not spending the same resources and latency on a simple residential water bill as you are on a 12-page consolidated commercial electricity invoice with net metering and prior-period adjustments.

---

### Pass 1A: Vision Extraction — Structure & Metering

**Purpose:** Extract the "envelope" of the invoice: who, where, when, what meters, what consumption.

**Model:** Claude Sonnet 4 (or GPT-4o). Vision mode. Temperature 0.0.

**Input:** All invoice page images + any extracted text as supplementary context.

**Prompt (abbreviated):**
```
SYSTEM:
You are an expert energy utility invoice analyst.
Focus ONLY on structural and metering data in this pass.
Do NOT extract charge line items — that will be done separately.

Extract:
1. Invoice identification (number, date, due date, statement type)
2. Billing period (start, end, days)
3. Account information (number, customer name, addresses)
4. Utility provider and supplier (if different)
5. Rate schedule / tariff code
6. ALL meters:
   - Meter number, read type (actual/estimated), read dates
   - Previous and current reads, multiplier, loss factor
   - Consumption (value, unit)
   - Demand (value, unit, type, peak datetime) if present
   - TOU breakdown if present
   - Generation/net metering data if present
7. Language: extract in original language AND English translation

For each value, note the page and approximate location.
Flag anything ambiguous.
Do NOT guess or infer. If unclear, extract what is visible and
mark confidence as low.

[Energy domain knowledge — metering section from Section 1]
[Few-shot examples from correction store, if available for this utility]

Output as JSON following this schema:
{pass_1a_schema}
```

**Why separate from charges?** Isolation of failure modes. If the model misreads a meter multiplier, it won't contaminate charge extraction in the same call. Debugging is surgical: "Pass 1A got the multiplier wrong" vs. "something went wrong somewhere in the giant extraction."

---

### Pass 1B: Vision Extraction — Charges & Financial

**Purpose:** Extract all charge line items, totals, taxes, credits, and adjustments.

**Model:** Same model as 1A. Vision mode. Temperature 0.0.

**Input:** All invoice page images + Pass 1A output (so the model knows the billing period, meters, etc.).

**Prompt (abbreviated):**
```
SYSTEM:
You are an expert energy utility invoice analyst.
Focus ONLY on charge line items and financial data in this pass.

You have already extracted structural data (provided below).
Now extract ALL charge line items.

For EACH line item, extract:
1. Description (exactly as printed)
2. Category: energy | demand | fixed | rider | tax | penalty | credit | adjustment | minimum | other
3. Charge owner: utility | supplier | government | other
4. Charge section: supply | distribution | taxes | other
5. Quantity and unit (if present)
6. Rate and unit (if present)
7. Amount
8. TEMPORAL ATTRIBUTION:
   - Does this charge apply to the current billing period?
   - Or does it reference a prior period, rolling average, or estimate?
   - Look for language like "adjustment", "true-up", "prior period",
     "based on [month/year]", "capacity obligation for [date]"
   - If it references a different period, capture that period.
9. Which meter does this charge apply to? (if multi-meter)

Also extract:
- Section subtotals (supply, distribution, taxes)
- Current charges total
- Previous balance, payments, late fees
- Total amount due
- Budget billing amount (if applicable)
- Whether a minimum bill was applied

[Energy domain knowledge — charges section from Section 1]
[Known issues for this utility from correction store]

Structural context from Pass 1A:
{pass_1a_output}

Output as JSON following this schema:
{pass_1b_schema}
```

---

### Pass 2: Structured Schema Mapping (Text LLM)

**Purpose:** Merge Pass 1A and 1B outputs into the canonical schema with normalization and classification.

**Model:** Claude Haiku 4.5. No vision needed — input is JSON. Temperature 0.0.

**What this pass does:**

1. **Merge** 1A (structure) and 1B (charges) into single schema.

2. **Unit Normalization:**
   - Gas: all to therms. Store original.
   - Electric: kWh for energy, kW for demand. Store original.
   - Water: gallons. Store original.
   - Include normalization formula in output.

3. **Charge Classification Refinement:**
   - Ensure every charge has `category`, `charge_owner`, `charge_section`.
   - Apply commodity-specific rules (e.g., "Customer Charge" → `fixed`, "SBC" on electric → `rider`).

4. **Temporal Attribution Enforcement:**
   - Every charge gets a `charge_period`.
   - Default: same as invoice billing period.
   - Override if the extraction flagged a prior period, rolling average, etc.
   - For ICAP/capacity charges, check if the reference period differs.

5. **Translation Finalization:**
   - For non-English invoices, ensure all field values have English translations.
   - Store `original_value` and `translated_value`.

6. **Confidence Propagation:**
   - Per-field confidence from Passes 1A/1B flows through.
   - Schema mapping doesn't increase confidence, but can decrease it (e.g., if classification was ambiguous).

---

### Pass 3: Validation (Primarily Code)

**Purpose:** Deterministic, rule-based validation. This is where you build trust.

**Critical design change from v1:** Distinguish three kinds of math.

#### 3.1 Expected Math vs. Stated Math vs. Utility Math

```python
class MathDisposition:
    CLEAN = "clean"                      # Everything matches perfectly
    ROUNDING_ONLY = "rounding_variance"  # Off by ≤ $0.05, typical utility rounding
    MINIMUM_BILL = "minimum_bill"        # Stated > calculated, minimum applies
    UTILITY_ADJUSTMENT = "utility_adj"   # Utility applied a post-calculation adjustment
    DISCREPANCY = "discrepancy"          # Genuine extraction error likely

def validate_line_item_math(charge):
    """Validate a single charge line: quantity × rate ≈ amount."""
    if not charge.get('quantity') or not charge.get('rate'):
        return None  # Can't validate — fixed fee or no rate breakdown

    expected = round(charge['quantity']['value'] * charge['rate']['value'], 2)
    stated = charge['amount']['value']
    variance = abs(expected - stated)

    if variance == 0:
        return MathResult(MathDisposition.CLEAN, expected, stated, variance)
    elif variance <= 0.05:
        return MathResult(MathDisposition.ROUNDING_ONLY, expected, stated, variance)
    elif stated > expected and charge.get('category') == 'fixed':
        return MathResult(MathDisposition.MINIMUM_BILL, expected, stated, variance,
                         note="Possible minimum bill applied")
    elif variance <= stated * 0.02:  # Within 2% — likely a utility adjustment
        return MathResult(MathDisposition.UTILITY_ADJUSTMENT, expected, stated, variance,
                         note="Small variance — possible rider/adjustment applied post-calculation")
    else:
        return MathResult(MathDisposition.DISCREPANCY, expected, stated, variance)


def validate_totals(extraction):
    """Validate that line items sum to stated totals."""
    results = []

    # Sum by section
    for section in ['supply', 'distribution', 'taxes', 'other']:
        section_charges = [c for c in extraction['charges']
                          if c['charge_section'] == section]
        calculated_sum = sum(c['amount']['value'] for c in section_charges)
        stated_subtotal_key = f"{section}_subtotal"
        stated = extraction['totals'].get(stated_subtotal_key, {}).get('value')

        if stated is not None:
            variance = abs(calculated_sum - stated)
            if variance <= 0.05:
                results.append(SectionResult(section, "valid", calculated_sum, stated, variance))
            else:
                results.append(SectionResult(section, "mismatch", calculated_sum, stated, variance))

    # Total current charges
    all_charges_sum = sum(c['amount']['value'] for c in extraction['charges'])
    stated_total = extraction['totals']['current_charges']['value']
    total_variance = abs(all_charges_sum - stated_total)

    if total_variance <= 0.10:
        results.append(TotalResult("valid", all_charges_sum, stated_total, total_variance))
    elif extraction['totals'].get('minimum_bill_applied'):
        results.append(TotalResult("minimum_bill", all_charges_sum, stated_total, total_variance,
                                   note="Minimum bill: stated total exceeds calculated charges"))
    else:
        results.append(TotalResult("mismatch", all_charges_sum, stated_total, total_variance))

    # Account balance: prev_balance + current_charges - payments + late_fees = total_due
    # (validate if all components are present)

    return results
```

#### 3.2 Consumption & Metering Validation

```python
def validate_meters(extraction):
    results = []
    for meter in extraction['meters']:
        # Meter reads → consumption
        if meter.get('previous_read') and meter.get('current_read'):
            multiplier = meter.get('multiplier', {}).get('value', 1.0)
            calc = (meter['current_read'] - meter['previous_read']) * multiplier
            stated = meter['consumption']['raw_value']
            if abs(calc - stated) > 1:
                results.append(MeterError(meter['meter_number']['value'],
                    f"Read diff ({meter['current_read']}-{meter['previous_read']})×{multiplier} = {calc}, stated = {stated}"))

        # TOU sums to total
        if meter.get('tou_breakdown'):
            tou_sum = sum(t['consumption']['value'] for t in meter['tou_breakdown'])
            total = meter['consumption']['raw_value']
            if abs(tou_sum - total) > 1:
                results.append(MeterError(meter['meter_number']['value'],
                    f"TOU sum ({tou_sum}) ≠ total consumption ({total})"))

        # Net metering balance
        if meter.get('generation') and meter.get('net_consumption'):
            # import - export ≈ net (approximately, due to self-consumption)
            pass  # Complex — flag for review if components don't reconcile

    return results
```

#### 3.3 Logic Validation

```python
def validate_logic(extraction):
    warnings = []

    # Commodity-unit consistency
    commodity = extraction['classification']['commodity_type']
    for meter in extraction['meters']:
        unit = meter['consumption']['raw_unit']
        if commodity == 'electricity' and unit in ['therms', 'CCF', 'MCF', 'dekatherms']:
            warnings.append(LogicWarning("fatal", "Gas units on electricity invoice"))
        if commodity == 'natural_gas' and unit in ['kWh', 'kW']:
            warnings.append(LogicWarning("fatal", "Electric units on gas invoice"))

    # Billing period reasonableness
    days = extraction['invoice']['billing_period']['days']
    if days > 95 or days < 15:
        warnings.append(LogicWarning("non_fatal", f"Unusual billing period: {days} days"))

    # Negative amounts should only be on credits/adjustments
    for charge in extraction['charges']:
        if charge['amount']['value'] < 0 and charge['category'] not in ['credit', 'adjustment']:
            warnings.append(LogicWarning("non_fatal",
                f"Negative amount on non-credit line: {charge['description']['value']}"))

    # Demand charges expected but missing?
    if extraction['classification']['has_demand_charges']:
        has_demand_line = any(c['category'] == 'demand' for c in extraction['charges'])
        if not has_demand_line:
            warnings.append(LogicWarning("non_fatal",
                "Classification detected demand charges but none found in extraction"))

    # TOU expected but missing?
    if extraction['classification']['has_tou']:
        has_tou_data = any(m.get('tou_breakdown') for m in extraction['meters'])
        if not has_tou_data:
            warnings.append(LogicWarning("non_fatal",
                "Classification detected TOU but no TOU breakdown found"))

    # Supplier split expected but all charges are same owner?
    if extraction['classification']['has_supplier_split']:
        owners = set(c['charge_owner'] for c in extraction['charges'])
        if len(owners) <= 1:
            warnings.append(LogicWarning("non_fatal",
                "Supplier split expected but all charges have same owner"))

    return warnings
```

#### 3.4 Correction-Based Auto-Repair (LLM — targeted)

For DISCREPANCY-level math errors only, send the specific error + relevant page back to the LLM:

```
The extraction shows {error_description}.
Specifically:
- Extracted quantity: {qty}, rate: {rate}
- Expected amount: {expected}, but extraction shows: {stated}
- This appears on page {N}.

Look at page {N} and determine: is the extraction wrong,
or is the invoice showing a non-standard calculation?

Respond with:
1. corrected_value (or confirm original)
2. explanation
3. is_utility_adjustment: true/false
```

---

### Pass 4: Conditional Audit (Second Vision LLM Call)

**Purpose:** Independent cross-verification using a DIFFERENT model. Questions are conditional on the classification.

**Model:** Use a different provider than Pass 1. If Pass 1 = Claude, Pass 4 = GPT-4o (or vice versa).

**Key principle:** Do NOT send the extraction. Send ONLY the original invoice images and specific questions. Fresh eyes.

**Base Questions (always asked):**
```
1. What is the total amount due on this invoice?
2. What is the billing period (start and end dates)?
3. What is the account number?
4. What is the total consumption shown, and in what units?
5. How many meters are listed?
```

**Conditional Questions (added based on classification):**

```python
def build_audit_questions(classification):
    questions = BASE_QUESTIONS.copy()

    if classification['has_demand_charges']:
        questions.append("Is there a demand charge (kW or kVA)? If so, what is the demand value and the demand charge amount?")

    if classification['has_tou']:
        questions.append("Are there time-of-use rate tiers? If so, list each tier name and its consumption amount.")

    if classification['has_supplier_split']:
        questions.append("Are charges split between a utility/distribution company and a separate supplier? If so, name both entities and their respective subtotals.")

    if classification['has_net_metering']:
        questions.append("Is there solar generation, net metering, or export credits shown? If so, what are the generation, export, and net values?")

    if classification['has_prior_period_adjustments']:
        questions.append("Are there any charges labeled as adjustments, true-ups, or corrections for a prior period? If so, what period do they reference?")

    if classification['commodity_type'] == 'electricity':
        questions.append("Are there any capacity charges (ICAP, PLC, transmission) that reference a different period than the billing period?")

    if classification['commodity_type'] == 'water':
        questions.append("Are water and sewer charges shown separately? What are the respective totals?")

    if classification['complexity_tier'] in ['complex', 'pathological']:
        questions.append("Are there any charges that appear to use a minimum bill or take-or-pay calculation?")
        questions.append("Do any line items show a quantity × rate that does NOT equal the stated amount?")

    return questions
```

**Comparison Logic:** Programmatically compare audit answers to extraction. Mismatches → flags.

```python
def compare_audit(extraction, audit_answers):
    mismatches = []

    # Total amount due
    audit_total = parse_currency(audit_answers['total_amount_due'])
    extraction_total = extraction['totals']['total_amount_due']['value']
    if abs(audit_total - extraction_total) > 0.50:
        mismatches.append(AuditMismatch("total_amount_due", extraction_total, audit_total, severity="fatal"))

    # Consumption
    audit_consumption = parse_quantity(audit_answers['consumption'])
    for meter in extraction['meters']:
        # Match by best-effort comparison
        # ...

    return mismatches
```

---

## 5. Confidence Gate — Weighted, Tiered Scoring

### 5.1 Field Weight Categories

```python
FIELD_WEIGHTS = {
    "fatal": {  # Any error here = forced human review
        "fields": ["total_amount_due", "account_number", "billing_period",
                   "commodity_type", "meter_consumption", "meter_multiplier"],
        "error_penalty": 1.0,  # Instant flag
    },
    "high": {  # Significant impact on extraction quality
        "fields": ["current_charges", "demand_value", "rate_schedule",
                   "section_subtotals", "tou_breakdown", "net_metering_values"],
        "error_penalty": 0.20,
    },
    "medium": {  # Important but recoverable
        "fields": ["individual_charge_amounts", "charge_classifications",
                   "meter_read_dates", "supplier_name"],
        "error_penalty": 0.08,
    },
    "low": {  # Nice to have, errors are tolerable
        "fields": ["rider_descriptions", "billing_address",
                   "late_fees", "previous_balance"],
        "error_penalty": 0.03,
    }
}
```

### 5.2 Scoring Algorithm

```python
def compute_confidence(extraction, validation, audit):
    score = 1.0
    fatal_triggered = False

    # --- Math validation ---
    for result in validation['math_results']:
        if result.disposition == "discrepancy":
            field_weight = get_field_weight(result.field)
            if field_weight == "fatal":
                fatal_triggered = True
            score -= FIELD_WEIGHTS[field_weight]['error_penalty']

    # Rounding and utility adjustments are NOT penalized
    # (they're expected behavior, not errors)

    # --- Audit mismatches ---
    for mismatch in audit['mismatches']:
        if mismatch.severity == "fatal":
            fatal_triggered = True
        score -= FIELD_WEIGHTS[mismatch.severity]['error_penalty']

    # --- Low per-field confidence ---
    for field_path, confidence in iter_field_confidences(extraction):
        if confidence < 0.80:
            weight = get_field_weight(field_path)
            if weight == "fatal":
                fatal_triggered = True
                score -= 0.15
            elif weight == "high":
                score -= 0.10
            elif weight == "medium":
                score -= 0.04
            # low: no additional penalty

    # --- Image quality ---
    if extraction['extraction_metadata']['source_document']['image_quality_score'] < 0.6:
        score -= 0.10

    # --- OCR penalty ---
    if extraction['extraction_metadata']['source_document']['ocr_applied']:
        score -= 0.03

    # --- Complexity adjustment ---
    # Complex invoices get slightly more lenient thresholds (more room for minor issues)
    complexity = extraction['classification']['complexity_tier']

    score = max(score, 0.0)

    return ConfidenceResult(
        score=score,
        fatal_triggered=fatal_triggered,
        tier=determine_tier(score, fatal_triggered, complexity)
    )


def determine_tier(score, fatal_triggered, complexity):
    if fatal_triggered:
        return "full_review"

    if complexity in ["complex", "pathological"]:
        if score >= 0.90:
            return "auto_accept"
        elif score >= 0.75:
            return "targeted_review"
        else:
            return "full_review"
    else:  # simple, standard
        if score >= 0.95:
            return "auto_accept"
        elif score >= 0.82:
            return "targeted_review"
        else:
            return "full_review"
```

### 5.3 Routing Summary

| Condition | Action |
|---|---|
| Fatal field error or audit mismatch | → Full human review (always) |
| Pathological complexity tier | → Full human review (always) |
| Score ≥ threshold for tier | → Auto-accept |
| Score between thresholds | → Targeted review: show only flagged fields |
| Score below lower threshold | → Full review |

---

## 6. Human Review — Minimal Interface

**Design constraint:** The main entry point is elsewhere. This UI exists only for the correction workflow.

### 6.1 Scope

This is NOT a full invoice management UI. It is:
- A correction queue viewer.
- A side-by-side comparison tool.
- A field-level approval/edit interface.

### 6.2 Minimal Screens

**Screen 1: Queue**
- Table of invoices pending review.
- Columns: Invoice #, Utility, Commodity, Confidence Score, Flags, Assigned To, Status.
- Filter by: confidence tier, commodity, utility, date.
- Sort by: priority (lowest confidence first).

**Screen 2: Review (the core screen)**
- **Left pane:** Original invoice (PDF/image viewer, zoomable, page navigation).
- **Right pane:** Extracted data as an editable form.
  - Each field has a colored confidence indicator (green ≥ 0.90, yellow 0.70–0.89, red < 0.70).
  - Flagged fields are highlighted and sorted to top.
  - Each flagged field shows: the extracted value, the validation error or audit mismatch, and the LLM's reasoning (from traceability).
- **Actions per field:** Approve / Edit / Flag as "extraction cannot determine."
- **Bulk actions:** "Approve all green fields" button.
- **Submit:** Sends corrections to the feedback store.

**Screen 3: Not needed.** No dashboards, no analytics, no settings. Those live in the main application.

### 6.3 Tech Stack for UI

- Azure Static Web Apps (minimal hosting cost).
- React + simple component library.
- PDF.js for invoice rendering.
- API calls to the extraction backend for data.

---

## 7. Learning & Feedback Loop

### 7.1 Correction Store Schema

```json
{
  "correction_id": "uuid",
  "extraction_id": "uuid",
  "file_hash": "sha256",
  "timestamp": "ISO-8601",
  "corrector_id": "analyst-042",
  "field_path": "charges[2].amount.value",
  "extracted_value": 23.66,
  "corrected_value": 26.63,
  "correction_type": "value_error | classification_error | missing_field | spurious_field | structural_error",
  "correction_reason": "Misread digit: 3 read as 6",
  "field_weight_category": "medium",
  "invoice_context": {
    "utility": "ConEdison",
    "commodity": "electricity",
    "complexity_tier": "standard",
    "format_fingerprint": "coned-commercial-2024-v2",
    "rate_schedule": "SC-9 Rate II"
  }
}
```

### 7.2 Three Learning Mechanisms

**Mechanism A: Dynamic Few-Shot Injection**

Before extraction, query the correction store for relevant history:

```python
def get_few_shot_context(utility, commodity, format_fingerprint):
    # Find corrections for this utility/commodity combo
    corrections = query_correction_store(
        utility=utility,
        commodity=commodity,
        format_fingerprint=format_fingerprint,
        limit=10,
        min_recurrence=2  # Only inject if the same mistake happened 2+ times
    )

    # Group by pattern
    patterns = group_by_pattern(corrections)

    # Format as prompt injection
    context = "KNOWN ISSUES FOR THIS INVOICE FORMAT:\n"
    for pattern in patterns:
        context += f"- {pattern.description} (occurred {pattern.count} times)\n"
        context += f"  Example: field '{pattern.field_path}' was extracted as "
        context += f"'{pattern.example_extracted}' but should be '{pattern.example_corrected}'\n"

    return context
```

This gets injected into both Pass 1A and Pass 1B prompts.

**Mechanism B: Format Fingerprinting**

Over time, build a library of recognized invoice layouts:

```json
{
  "fingerprint_id": "coned-commercial-2024-v2",
  "utility": "ConEdison",
  "commodity": "electricity",
  "detection_signals": {
    "logo_text": "ConEdison",
    "header_pattern": "Your Energy Statement",
    "table_structure": "supply-then-delivery-then-taxes"
  },
  "known_issues": [
    "Decimal point on demand value is faint — commonly misread as integer",
    "Meter multiplier is in small footer text below meter table",
    "ICAP charge references a capacity period 18 months prior"
  ],
  "custom_prompt_additions": "...",
  "custom_validation_rules": ["rule_coned_multiplier", "rule_coned_icap_period"],
  "accuracy_history": [0.88, 0.92, 0.95, 0.97],
  "invoices_processed": 47
}
```

**Mechanism C: Automated Validation Rule Expansion**

When corrections cluster around a pattern, generate a new validation rule:

```python
def detect_rule_candidates(correction_store):
    """Analyze corrections to find patterns that should become validation rules."""
    patterns = correction_store.group_by(
        keys=["utility", "field_path", "correction_type"],
        min_count=5  # At least 5 occurrences
    )

    candidates = []
    for pattern in patterns:
        candidates.append({
            "pattern": pattern,
            "suggested_rule": generate_rule_description(pattern),
            "confidence": pattern.count / pattern.total_invoices_for_utility,
            "requires_human_approval": True  # Always review before deploying
        })

    return candidates
```

### 7.3 What This Is NOT

This is NOT fine-tuning. Fine-tuning would:
- Require thousands of examples to be effective.
- Make the model less general (overfitting risk).
- Destroy traceability (can't explain why behavior changed).
- Be expensive and slow to iterate.
- Make you dependent on model provider retraining cycles.

The few-shot + fingerprint + rule approach is:
- Traceable (every addition links to specific corrections).
- Instant (next invoice benefits immediately).
- Reversible (remove an addition if it causes regressions).
- Auditable (you can show exactly what knowledge the system uses).
- Cheap (no training compute).

---

## 8. Bounded-Variance & Auditability Strategy

### 8.1 Honest Framing

This system does NOT guarantee deterministic output. It guarantees **bounded variance with full auditability**.

What this means:
- The same invoice processed with the same pipeline version will *almost always* produce identical output.
- When it doesn't (and it won't, occasionally), the system detects and logs the variance.
- Every output can be traced back to exactly what produced it.

### 8.2 Variance Sources & Mitigations

| Source | Likelihood | Mitigation |
|---|---|---|
| GPU float nondeterminism in LLM inference | Low (~5% of calls) | Detect via output hash comparison; log as drift event. |
| API routing to different hardware | Low | Use seed parameter where available; accept as bounded variance. |
| Image preprocessing drift | Very low (if library versions pinned) | Hash normalized images; detect drift. |
| Model version change | **Certain** (when you upgrade) | Pin versions; run regression suite before upgrading. |
| Prompt version change | **Certain** (when you improve prompts) | Version control all prompts; run regression suite before deploying. |
| Few-shot context change | Frequent (as correction store grows) | Hash the few-shot injection; include hash in extraction metadata. |

### 8.3 Drift Detection

On any re-processing of a previously-processed invoice:

```python
def detect_drift(new_extraction, previous_extraction):
    """Compare two extractions of the same invoice."""
    drift_fields = []

    for field_path in all_field_paths(new_extraction):
        new_val = get_value(new_extraction, field_path)
        old_val = get_value(previous_extraction, field_path)

        if new_val != old_val:
            drift_fields.append({
                "field": field_path,
                "previous": old_val,
                "current": new_val,
                "field_weight": get_field_weight(field_path)
            })

    if drift_fields:
        return DriftEvent(
            extraction_id=new_extraction['extraction_metadata']['extraction_id'],
            previous_id=previous_extraction['extraction_metadata']['extraction_id'],
            fields=drift_fields,
            fatal_drift=any(f['field_weight'] == 'fatal' for f in drift_fields),
            cause_hypothesis=diagnose_drift_cause(new_extraction, previous_extraction)
        )

    return None
```

**Drift events are first-class.** They are logged, they trigger alerts if fatal fields are involved, and they feed back into the confidence scoring of both the new and old extractions.

### 8.4 Reproducibility Package

Every extraction stores everything needed to understand (and attempt to reproduce) it:

```json
{
  "reproducibility": {
    "pipeline_version": "v2.1.0",
    "input_file_hash": "sha256",
    "normalized_image_hash": "sha256",
    "model_versions": {
      "classification": "claude-haiku-4-5-20251001",
      "extraction": "claude-sonnet-4-20250514",
      "audit": "gpt-4o-2024-11-20"
    },
    "prompt_hashes": {
      "pass_0_5": "sha256",
      "pass_1a": "sha256",
      "pass_1b": "sha256",
      "pass_2": "sha256",
      "pass_4": "sha256"
    },
    "few_shot_context_hash": "sha256 or null",
    "format_fingerprint_version": "coned-commercial-2024-v2:v3",
    "validation_rules_hash": "sha256",
    "temperature": 0.0,
    "seed": 42,
    "raw_model_responses": {
      "pass_1a_response_hash": "sha256",
      "pass_1b_response_hash": "sha256",
      "pass_4_response_hash": "sha256"
    }
  }
}
```

---

## 9. Azure-First Technology Stack

| Component | Azure Service | Rationale |
|---|---|---|
| **LLM (extraction)** | Azure OpenAI (GPT-4o) or direct Anthropic API for Claude | Azure OpenAI gives you data residency + enterprise SLA. Use Claude via API if preferred for extraction quality. |
| **LLM (audit)** | Whichever model you did NOT use for extraction | Model diversity. If extraction = Claude, audit = Azure OpenAI GPT-4o. |
| **LLM (classification, schema mapping)** | Azure OpenAI (GPT-4o-mini) or Claude Haiku | Cheap, fast, good enough for structured tasks. |
| **OCR (fallback)** | Azure AI Document Intelligence | Strong OCR, table extraction, layout analysis. Can supplement vision LLM for degraded images. |
| **Language Detection & Translation** | Azure AI Translator | Built-in language detection + translation. |
| **Queue / Orchestration** | Azure Service Bus + Azure Functions | Service Bus for durable message queuing. Functions for pass orchestration (consumption-based billing). |
| **Compute (pipeline)** | Azure Container Apps (scale-to-zero) | Cost-effective for bursty workloads. Scale to zero when idle. Aligns with your existing interest in ACA. |
| **Document Storage** | Azure Blob Storage | Store original invoices, normalized images, extraction results. Lifecycle policies for archival. |
| **Structured Data** | Azure SQL Database (or PostgreSQL Flexible Server) | Extraction results, correction store, format fingerprints, audit trail. |
| **Human Review UI** | Azure Static Web Apps | Minimal hosting. React SPA calling backend APIs. |
| **Backend API** | Azure Functions or Azure Container Apps | REST API for the review UI and external integrations. |
| **Monitoring** | Azure Monitor + Application Insights | Pipeline health, latency, error rates, accuracy metrics. |
| **Prompt & Config Storage** | Azure Blob Storage (versioned containers) or Azure App Configuration | Prompt templates, few-shot libraries, validation rules. Git-synced. |
| **Secrets** | Azure Key Vault | API keys for LLM providers. |

### Architecture Diagram (Azure)

```
                        ┌─────────────────────┐
                        │  Invoice Ingestion   │
                        │  (API / Blob trigger)│
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Azure Service Bus   │
                        │  (extraction queue)   │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Azure Container App │
                        │  (Pipeline Workers)  │
                        │  Scale-to-zero       │
                        │                      │
                        │  Pass 0 → 0.5 → 1A  │
                        │  → 1B → 2 → 3 → 4   │
                        └──┬──────────┬────────┘
                           │          │
              ┌────────────▼─┐   ┌────▼───────────┐
              │ Azure OpenAI │   │ Anthropic API   │
              │ (GPT-4o)     │   │ (Claude Sonnet) │
              └──────────────┘   └────────────────┘
                           │
                ┌──────────▼──────────┐
                │  Azure SQL Database  │
                │  - Extractions       │
                │  - Corrections       │
                │  - Fingerprints      │
                │  - Audit trail       │
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
    ┌─────────▼─────────┐   ┌──────────▼──────────┐
    │  Auto-Accept       │   │  Human Review Queue  │
    │  → Output API      │   │  → Static Web App    │
    └───────────────────┘   └─────────────────────┘
```

---

## 10. Cost Analysis (Azure)

### 10.1 Per-Invoice Cost

| Pass | Model | Estimated Cost |
|---|---|---|
| Pass 0 (preprocessing) | Compute only | ~$0.001 |
| Pass 0.5 (classification) | GPT-4o-mini / Haiku | ~$0.003 |
| Pass 1A (structure extraction) | Claude Sonnet / GPT-4o | ~$0.02–0.03 |
| Pass 1B (charge extraction) | Claude Sonnet / GPT-4o | ~$0.02–0.04 |
| Pass 2 (schema mapping) | GPT-4o-mini / Haiku | ~$0.004 |
| Pass 3 (validation) | Code only | ~$0.001 |
| Pass 4 (audit) | GPT-4o / Claude Sonnet | ~$0.02 |
| **LLM total per invoice** | | **$0.07 – $0.12** |
| Azure compute + storage | | ~$0.01 |
| **Total per invoice (no human)** | | **$0.08 – $0.13** |

### 10.2 Blended Cost Including Human Review

Assuming human review costs ~$2.00/invoice:

| Scenario | Human Review Rate | Blended Cost/Invoice |
|---|---|---|
| Early (first month) | ~40% | ~$0.90 |
| Stabilized (3 months) | ~20% | ~$0.50 |
| Mature (6+ months) | ~8–12% | ~$0.25–0.35 |
| Optimized (12+ months) | ~3–5% | ~$0.15–0.20 |

### 10.3 vs. Fully Manual

If current human processing costs $3–5/invoice, break-even happens almost immediately, and the cost advantage grows as the system learns.

---

## 11. Scalability

| Volume | Infrastructure | Throughput |
|---|---|---|
| < 500/day | 1 Container App instance, scale-to-zero | Sufficient |
| 500–5,000/day | 2–5 Container App replicas | ~500/hour |
| 5,000–50,000/day | 10–20 replicas + batch API calls | ~5,000/hour |
| 50,000+ | Multi-region + batch APIs + multiple LLM providers | ~25,000/hour |

**Rate limiting is the real constraint.** Azure OpenAI has TPM (tokens per minute) limits. For high volume, request limit increases or use the Batch API (50% cost reduction, results within 24 hours).

---

## 12. Implementation Sequence

### Phase 1: Foundation (Weeks 1–4)
- Pass 0 (PDF → images, text extraction, language detection).
- Pass 0.5 (classification — simple version, just commodity + complexity).
- Pass 1A + 1B (core extraction with energy-specific prompts).
- Pass 2 (schema mapping with unit normalization).
- Pass 3 (math validation — expected vs. stated, basic logic checks).
- Output to JSON.
- Test against 50 real invoices (mix of gas, electric, water; simple and complex).
- Azure infrastructure: Container App + Blob Storage + SQL Database.

### Phase 2: Quality & Review (Weeks 5–8)
- Pass 4 (conditional audit with model diversity).
- Confidence scoring (weighted, tiered).
- Human review queue + minimal correction UI.
- Correction store.
- Billing math vs. utility math handling (minimum bills, rounding).
- Temporal attribution on charges.
- Expand validation rules based on Phase 1 findings.
- Test against 200+ invoices.

### Phase 3: Learning & Hardening (Weeks 9–12)
- Format fingerprinting (auto-detection of known invoice layouts).
- Dynamic few-shot injection from correction store.
- Non-English invoice pipeline (translation + dual extraction).
- Drift detection on re-processed invoices.
- Regression test suite (golden set of invoices with expected outputs).
- Accuracy dashboard (built into the main application, not the review UI).

### Phase 4: Scale & Optimize (Weeks 13–16)
- Azure Service Bus queue-based processing.
- Batch API integration for overnight/bulk processing.
- Multi-provider LLM failover (Claude primary, GPT-4o fallback, or vice versa).
- Cost optimization: route simple invoices to cheaper models.
- Automated validation rule candidates from correction patterns.
- Performance monitoring and alerting.

---

## 13. Key Metrics to Track

| Metric | Target (Mature System) |
|---|---|
| **Extraction accuracy** (field-level, post-validation) | > 97% |
| **Auto-accept rate** | > 85% of invoices |
| **Fatal field error rate** | < 2% |
| **Human review time per invoice** | < 90 seconds (targeted review) |
| **End-to-end processing time** | < 60 seconds (auto-accept path) |
| **Cost per invoice (blended)** | < $0.30 |
| **Drift rate on re-processing** | < 3% of fields |
| **Format fingerprint coverage** | > 80% of invoices match a known format |
