"""Common output schema for extracted invoice data.

Every extracted value carries its own confidence score and source location.
The schema supports both US and international (EU) invoice formats including
VAT, calorific conversion, contracted capacity, and locale-aware parsing.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Generic value wrappers
# ---------------------------------------------------------------------------


class ConfidentValue(BaseModel, Generic[T]):
    """A single extracted value with its confidence score and source location."""

    value: T
    confidence: float = Field(ge=0.0, le=1.0)
    source_location: str | None = None


class MonetaryAmount(BaseModel):
    """A monetary value with currency, the original string for traceability,
    confidence, and source location."""

    value: float
    currency: str = "USD"
    original_string: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source_location: str | None = None


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class CommodityType(StrEnum):
    NATURAL_GAS = "natural_gas"
    ELECTRICITY = "electricity"
    WATER = "water"
    MULTI_COMMODITY = "multi_commodity"


class ComplexityTier(StrEnum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    PATHOLOGICAL = "pathological"


class ConfidenceTier(StrEnum):
    AUTO_ACCEPT = "auto_accept"
    TARGETED_REVIEW = "targeted_review"
    FULL_REVIEW = "full_review"


class ChargeCategory(StrEnum):
    ENERGY = "energy"
    DEMAND = "demand"
    FIXED = "fixed"
    RIDER = "rider"
    TAX = "tax"
    PENALTY = "penalty"
    CREDIT = "credit"
    ADJUSTMENT = "adjustment"
    MINIMUM = "minimum"
    OTHER = "other"


class ChargeOwner(StrEnum):
    UTILITY = "utility"
    SUPPLIER = "supplier"
    GOVERNMENT = "government"
    OTHER = "other"


class ChargeSection(StrEnum):
    SUPPLY = "supply"
    DISTRIBUTION = "distribution"
    TAXES = "taxes"
    OTHER = "other"


class ReadType(StrEnum):
    ACTUAL = "actual"
    ESTIMATED = "estimated"
    CUSTOMER = "customer"


class DemandType(StrEnum):
    NON_COINCIDENT = "non_coincident"
    COINCIDENT = "coincident"
    REACTIVE = "reactive"


class AttributionType(StrEnum):
    CURRENT = "current"
    PRIOR_PERIOD = "prior_period"
    ROLLING_AVERAGE = "rolling_average"
    ESTIMATED = "estimated"
    PRORATED = "prorated"


class StatementType(StrEnum):
    REGULAR = "regular"
    FINAL = "final"
    ESTIMATED = "estimated"
    CORRECTED = "corrected"
    CREDIT_MEMO = "credit_memo"


class MathDisposition(StrEnum):
    CLEAN = "clean"
    ROUNDING_VARIANCE = "rounding_variance"
    MINIMUM_BILL = "minimum_bill"
    UTILITY_ADJUSTMENT = "utility_adjustment"
    DISCREPANCY = "discrepancy"


class VATCategory(StrEnum):
    STANDARD = "standard"
    REDUCED = "reduced"
    ZERO = "zero"
    EXEMPT = "exempt"
    REVERSE_CHARGE = "reverse_charge"


class MarketModel(StrEnum):
    REGULATED = "regulated"
    DEREGULATED = "deregulated"
    LIBERALIZED_EU = "liberalized_eu"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Extraction metadata
# ---------------------------------------------------------------------------


class ModelInfo(BaseModel):
    """Identifies the model and temperature used for a pipeline pass."""

    model: str
    temperature: float = 0.0


class SourceDocument(BaseModel):
    """Information about the original source document."""

    file_hash: str
    file_type: str
    page_count: int
    pages_used: list[int] = Field(default_factory=list)
    pages_discarded: list[int] = Field(default_factory=list)
    ocr_applied: bool = False
    image_quality_score: float = Field(ge=0.0, le=1.0, default=0.0)
    language_detected: str = "en"
    language_translated: bool = False


class CurrencyInfo(BaseModel):
    """Locale-specific currency details."""

    code: str = "USD"
    symbol: str = "$"
    decimal_separator: str = "."
    thousands_separator: str = ","


class LocaleContext(BaseModel):
    """Full locale context detected during ingestion."""

    country_code: str | None = None
    country_name: str | None = None
    language: str = "en"
    currency: CurrencyInfo = Field(default_factory=CurrencyInfo)
    date_format_detected: str | None = None
    number_format_detected: str | None = None
    tax_regime: str | None = None
    regulatory_body: str | None = None
    market_model: MarketModel = MarketModel.UNKNOWN


class ExtractionMetadata(BaseModel):
    """Metadata for a single extraction run."""

    extraction_id: UUID = Field(default_factory=uuid4)
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_version: str = "v2.1.0"
    models_used: dict[str, ModelInfo] = Field(default_factory=dict)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    few_shot_context_hash: str | None = None
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence_tier: ConfidenceTier = ConfidenceTier.FULL_REVIEW
    flags: list[str] = Field(default_factory=list)
    processing_time_ms: int = 0
    source_document: SourceDocument = Field(default_factory=lambda: SourceDocument(file_hash="", file_type="unknown", page_count=0))
    locale_context: LocaleContext | None = None


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class Classification(BaseModel):
    """Pass 0.5 classification result."""

    commodity_type: CommodityType
    commodity_confidence: float = Field(ge=0.0, le=1.0)
    complexity_tier: ComplexityTier
    complexity_signals: list[str] = Field(default_factory=list)
    market_type: MarketModel = MarketModel.UNKNOWN
    has_supplier_split: bool = False
    has_demand_charges: bool = False
    has_tou: bool = False
    has_net_metering: bool = False
    has_prior_period_adjustments: bool = False
    estimated_line_item_count: int = 0
    format_fingerprint: str = "unknown"
    has_multiple_vat_rates: bool = False
    has_calorific_conversion: bool = False
    has_contracted_capacity: bool = False


# ---------------------------------------------------------------------------
# Invoice header
# ---------------------------------------------------------------------------


class BillingPeriod(BaseModel):
    """Start/end dates and duration of the billing period."""

    start: ConfidentValue[date]
    end: ConfidentValue[date]
    days: int


class Invoice(BaseModel):
    """Invoice-level header information."""

    invoice_number: ConfidentValue[str]
    invoice_date: ConfidentValue[date | None]
    due_date: ConfidentValue[date | None]
    billing_period: BillingPeriod | None = None
    rate_schedule: ConfidentValue[str] | None = None
    statement_type: StatementType = StatementType.REGULAR


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


class Account(BaseModel):
    """Customer / account information."""

    account_number: ConfidentValue[str]
    customer_name: ConfidentValue[str]
    service_address: ConfidentValue[str]
    billing_address: ConfidentValue[str] | None = None
    utility_provider: ConfidentValue[str]
    supplier: ConfidentValue[str] | None = None
    # European identifiers
    pod_pdl_pdr: ConfidentValue[str] | None = None
    ean_code: ConfidentValue[str] | None = None
    contract_number: ConfidentValue[str] | None = None
    network_operator: ConfidentValue[str] | None = None
    metering_operator: ConfidentValue[str] | None = None
    supplier_vat_number: ConfidentValue[str] | None = None
    customer_vat_number: ConfidentValue[str] | None = None


# ---------------------------------------------------------------------------
# Meters
# ---------------------------------------------------------------------------


class Consumption(BaseModel):
    """Consumption data with optional normalisation."""

    raw_value: float
    raw_unit: str
    normalized_value: float | None = None
    normalized_unit: str | None = None
    normalization_formula: str | None = None


class ConversionFactors(BaseModel):
    """Gas calorific value and volume correction factors (EU gas)."""

    calorific_value: ConfidentValue[float] | None = None
    volume_correction_factor: ConfidentValue[float] | None = None
    conversion_formula: str | None = None


class Demand(BaseModel):
    """Demand (peak) measurement."""

    value: float
    unit: str
    demand_type: DemandType
    peak_datetime: datetime | None = None
    source_location: str | None = None


class TOUPeriod(BaseModel):
    """A single time-of-use period breakdown."""

    period: str
    consumption: ConfidentValue[float]
    demand: ConfidentValue[float] | None = None


class ContractedCapacity(BaseModel):
    """European contracted/subscribed capacity for a meter."""

    value: float
    unit: str
    source_location: str | None = None


class Meter(BaseModel):
    """A single meter on the invoice with reads, consumption, and demand."""

    meter_number: ConfidentValue[str]
    service_point_id: str | None = None
    read_type: ReadType = ReadType.ACTUAL
    read_date_start: date | None = None
    read_date_end: date | None = None
    previous_read: float | None = None
    current_read: float | None = None
    multiplier: ConfidentValue[float] | None = None
    loss_factor: ConfidentValue[float] | None = None
    consumption: Consumption
    demand: Demand | None = None
    generation: float | None = None
    net_consumption: float | None = None
    tou_breakdown: list[TOUPeriod] | None = None
    conversion_factors: ConversionFactors | None = None
    contracted_capacity: ContractedCapacity | None = None


# ---------------------------------------------------------------------------
# Charges
# ---------------------------------------------------------------------------


class ChargePeriod(BaseModel):
    """Temporal attribution for a charge line."""

    start: date
    end: date
    attribution_type: AttributionType = AttributionType.CURRENT
    reference_period_note: str | None = None


class MathCheck(BaseModel):
    """Per-line math verification result."""

    expected_amount: float
    calculation: str
    matches_stated: bool
    variance: float
    utility_adjustment_detected: bool = False
    adjustment_note: str | None = None


class Charge(BaseModel):
    """A single charge line item."""

    line_id: str
    description: ConfidentValue[str]
    category: ChargeCategory
    subcategory: str | None = None
    charge_owner: ChargeOwner
    charge_section: ChargeSection
    quantity: ConfidentValue[float] | None = None
    rate: ConfidentValue[float] | None = None
    amount: MonetaryAmount
    charge_period: ChargePeriod | None = None
    applies_to_meter: str | None = None
    math_check: MathCheck | None = None
    # VAT / international fields
    amount_net: MonetaryAmount | None = None
    vat_rate: float | None = None
    vat_amount: MonetaryAmount | None = None
    amount_gross: MonetaryAmount | None = None
    vat_category: VATCategory | None = None


# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------


class VATSummaryEntry(BaseModel):
    """A single row from the VAT summary table."""

    vat_rate: float
    vat_category: VATCategory
    taxable_base: MonetaryAmount
    vat_amount: MonetaryAmount


class VATNumbers(BaseModel):
    """Supplier and customer VAT identification numbers."""

    supplier_vat: str | None = None
    customer_vat: str | None = None


class Totals(BaseModel):
    """Invoice total amounts."""

    supply_subtotal: MonetaryAmount | None = None
    distribution_subtotal: MonetaryAmount | None = None
    taxes_subtotal: MonetaryAmount | None = None
    current_charges: MonetaryAmount | None = None
    previous_balance: MonetaryAmount | None = None
    payments_received: MonetaryAmount | None = None
    late_fees: MonetaryAmount | None = None
    total_amount_due: MonetaryAmount | None = None
    budget_billing_amount: MonetaryAmount | None = None
    minimum_bill_applied: bool = False
    # VAT / international totals
    vat_summary: list[VATSummaryEntry] | None = None
    total_net: MonetaryAmount | None = None
    total_vat: MonetaryAmount | None = None
    total_gross: MonetaryAmount | None = None
    reverse_charge_applied: bool = False
    vat_numbers: VATNumbers | None = None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class MathResults(BaseModel):
    """Aggregate math validation results."""

    line_items_sum: float
    stated_current_charges: float
    difference: float
    line_items_sum_valid: bool
    section_subtotals_valid: bool
    account_balance_valid: bool
    notes: list[str] = Field(default_factory=list)


class UtilityMathAdjustment(BaseModel):
    """A detected utility-side math adjustment."""

    description: str
    expected_by_multiplication: float
    stated_on_invoice: float
    variance: float
    disposition: MathDisposition


class ConsumptionCrosschecks(BaseModel):
    """Cross-checks on consumption/metering data."""

    meter_reads_match_consumption: bool | None = None
    tou_sums_to_total: bool | None = None
    net_metering_balance_valid: bool | None = None
    notes: list[str] = Field(default_factory=list)


class LogicChecks(BaseModel):
    """Domain-specific logic validation flags."""

    commodity_unit_consistency: bool
    billing_period_reasonable: bool
    negative_amounts_on_credits_only: bool
    demand_present_if_expected: bool
    notes: list[str] = Field(default_factory=list)


class AuditMismatch(BaseModel):
    """A single field mismatch detected during the audit pass."""

    field: str
    extraction_value: Any
    audit_value: Any
    severity: str


class AuditResults(BaseModel):
    """Summary of the independent audit (Pass 4)."""

    fields_checked: int
    fields_matched: int
    fields_mismatched: int
    mismatches: list[AuditMismatch] = Field(default_factory=list)
    audit_model: str


class Validation(BaseModel):
    """Complete validation results."""

    math_results: MathResults
    utility_math_adjustments: list[UtilityMathAdjustment] = Field(default_factory=list)
    consumption_crosschecks: ConsumptionCrosschecks
    logic_checks: LogicChecks
    audit_results: AuditResults | None = None
    overall_math_disposition: MathDisposition


# ---------------------------------------------------------------------------
# Traceability & bounded variance
# ---------------------------------------------------------------------------


class TraceabilityEntry(BaseModel):
    """Traceability record for a single extracted field value."""

    field: str
    value: Any
    reasoning: str
    source_pages: list[int] = Field(default_factory=list)
    extraction_pass: str
    validated_by: list[str] = Field(default_factory=list)
    human_reviewed: bool = False
    confidence_factors: list[str] = Field(default_factory=list)


class BoundedVarianceRecord(BaseModel):
    """Record of drift detection when reprocessing a previously seen invoice."""

    is_reprocessing: bool = False
    previous_extraction_id: UUID | None = None
    drift_detected: bool = False
    drift_fields: list[str] = Field(default_factory=list)
    drift_disposition: str | None = None


# ---------------------------------------------------------------------------
# Top-level extraction result
# ---------------------------------------------------------------------------


class ExtractionResult(BaseModel):
    """The complete output of the extraction pipeline."""

    extraction_metadata: ExtractionMetadata
    classification: Classification
    invoice: Invoice
    account: Account
    meters: list[Meter] = Field(default_factory=list)
    charges: list[Charge] = Field(default_factory=list)
    totals: Totals
    validation: Validation | None = None
    traceability: list[TraceabilityEntry] = Field(default_factory=list)
    bounded_variance_record: BoundedVarianceRecord | None = None
