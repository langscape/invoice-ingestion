"""Internal inter-pass data models.

These models are used to pass data between pipeline passes and are not part of
the final extraction output schema.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from invoice_ingestion.models.schema import (
    CommodityType,
    ComplexityTier,
    MarketModel,
    MathDisposition,
)


# ---------------------------------------------------------------------------
# Pass 0 – Ingestion
# ---------------------------------------------------------------------------


class PageData(BaseModel):
    """A single normalised page image with optional extracted text."""

    page_number: int
    image_base64: str
    extracted_text: str | None = None
    language: str | None = None
    quality_score: float = 0.0


class IngestionResult(BaseModel):
    """Output of Pass 0 (ingestion and pre-processing)."""

    ingestion_id: UUID = Field(default_factory=uuid4)
    file_hash: str
    file_type: str
    normalized_image_hash: str | None = None
    image_quality_score: float
    pages: list[PageData]
    language_detected: str = "en"


# ---------------------------------------------------------------------------
# Pass 0.5 – Classification
# ---------------------------------------------------------------------------


class ClassificationResult(BaseModel):
    """Output of Pass 0.5 (classification and routing)."""

    commodity_type: CommodityType
    commodity_confidence: float
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
    language: str = "en"
    has_multiple_vat_rates: bool = False
    has_calorific_conversion: bool = False
    has_contracted_capacity: bool = False
    country_code: str | None = None
    number_format: str | None = None
    date_format: str | None = None


# ---------------------------------------------------------------------------
# Pass 1A – Structure & Metering Extraction
# ---------------------------------------------------------------------------


class Pass1AResult(BaseModel):
    """Raw extraction output from Pass 1A (headers, account, meters)."""

    invoice: dict
    account: dict
    meters: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pass 1B – Charges & Financial Extraction
# ---------------------------------------------------------------------------


class Pass1BResult(BaseModel):
    """Raw extraction output from Pass 1B (charges, totals)."""

    charges: list[dict] = Field(default_factory=list)
    totals: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pass 2 – Schema Mapping & Normalisation
# ---------------------------------------------------------------------------


class Pass2Result(BaseModel):
    """Merged and normalised extraction from Pass 2."""

    data: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pass 3 – Validation
# ---------------------------------------------------------------------------


class ValidationIssue(BaseModel):
    """A single validation problem discovered in Pass 3."""

    field: str
    severity: str  # "fatal", "warning", "info"
    message: str
    expected: str | None = None
    actual: str | None = None


class Pass3Result(BaseModel):
    """Aggregate validation output from Pass 3."""

    issues: list[ValidationIssue] = Field(default_factory=list)
    math_disposition: MathDisposition
    repairs_attempted: int = 0
    repairs_successful: int = 0


# ---------------------------------------------------------------------------
# Pass 4 – Audit
# ---------------------------------------------------------------------------


class AuditQuestion(BaseModel):
    """A question posed to the audit model and its response."""

    question: str
    answer: str | None = None
    field_to_check: str | None = None


class Pass4Result(BaseModel):
    """Output of the independent audit pass (Pass 4)."""

    questions_asked: list[AuditQuestion] = Field(default_factory=list)
    fields_checked: int = 0
    fields_matched: int = 0
    mismatches: list[dict] = Field(default_factory=list)
    audit_model: str = ""
