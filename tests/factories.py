"""Test data factories for building test objects."""
from uuid import uuid4
from invoice_ingestion.models.internal import (
    IngestionResult, PageData, ClassificationResult,
)
from invoice_ingestion.models.schema import (
    ExtractionResult, ExtractionMetadata, Classification, Invoice, Account,
    Meter, Charge, Totals, ConfidentValue, MonetaryAmount, SourceDocument,
    ModelInfo, ConfidenceTier, CommodityType, ComplexityTier, MarketModel,
    ChargeCategory, ChargeOwner, ChargeSection, ReadType, MathCheck,
    Consumption, BoundedVarianceRecord, StatementType,
)
from datetime import datetime, date, timezone
import base64


def make_page_data(page_number: int = 1, quality: float = 0.9, language: str = "en") -> PageData:
    # A tiny valid 1x1 PNG
    png_pixel = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82').decode()
    return PageData(
        page_number=page_number,
        image_base64=png_pixel,
        extracted_text=f"Sample invoice text for page {page_number}",
        language=language,
        quality_score=quality,
    )


def make_ingestion_result(
    pages: int = 3,
    quality: float = 0.85,
    language: str = "en",
    file_type: str = "pdf",
) -> IngestionResult:
    return IngestionResult(
        file_hash="abc123def456" * 5 + "abcd",
        file_type=file_type,
        image_quality_score=quality,
        pages=[make_page_data(i + 1, quality, language) for i in range(pages)],
        language_detected=language,
    )


def make_classification(
    commodity: str = "electricity",
    tier: str = "standard",
    signals: list[str] | None = None,
    has_demand: bool = False,
    has_tou: bool = False,
    has_supplier_split: bool = False,
    line_items: int = 15,
) -> ClassificationResult:
    return ClassificationResult(
        commodity_type=commodity,
        commodity_confidence=0.95,
        complexity_tier=tier,
        complexity_signals=signals or [],
        market_type="regulated",
        has_supplier_split=has_supplier_split,
        has_demand_charges=has_demand,
        has_tou=has_tou,
        has_net_metering=False,
        has_prior_period_adjustments=False,
        estimated_line_item_count=line_items,
        format_fingerprint="unknown",
        language="en",
    )


def make_charge(
    line_id: str = "L001",
    category: str = "energy",
    amount: float = 23.66,
    qty: float | None = 280.0,
    rate: float | None = 0.0845,
    section: str = "supply",
    owner: str = "utility",
    matches_stated: bool = True,
) -> dict:
    charge = {
        "line_id": line_id,
        "description": {"value": f"Test Charge {line_id}", "confidence": 0.95},
        "category": category,
        "subcategory": None,
        "charge_owner": owner,
        "charge_section": section,
        "amount": {"value": amount, "currency": "USD", "confidence": 0.96},
    }
    if qty is not None and rate is not None:
        charge["quantity"] = {"value": qty, "unit": "kWh"}
        charge["rate"] = {"value": rate, "unit": "$/kWh"}
        expected = round(qty * rate, 2)
        charge["math_check"] = {
            "expected_amount": expected,
            "calculation": f"{qty} x {rate} = {expected}",
            "matches_stated": matches_stated,
            "variance": abs(expected - amount),
            "utility_adjustment_detected": False,
        }
    return charge


def make_meter(
    meter_id: str = "M-001",
    consumption: float = 750.0,
    unit: str = "kWh",
    read_type: str = "actual",
    prev_read: float | None = 45230,
    curr_read: float | None = 45980,
    multiplier: float = 1.0,
    tou: list[dict] | None = None,
    demand: dict | None = None,
) -> dict:
    meter = {
        "meter_number": {"value": meter_id, "confidence": 0.96},
        "read_type": read_type,
        "consumption": {"raw_value": consumption, "raw_unit": unit},
    }
    if prev_read is not None:
        meter["previous_read"] = prev_read
    if curr_read is not None:
        meter["current_read"] = curr_read
    if multiplier != 1.0:
        meter["multiplier"] = {"value": multiplier, "confidence": 0.9}
    if tou:
        meter["tou_breakdown"] = tou
    if demand:
        meter["demand"] = demand
    return meter


def make_extraction_dict(
    charges: list[dict] | None = None,
    meters: list[dict] | None = None,
    commodity: str = "electricity",
    total_amount: float = 187.45,
    current_charges: float = 187.45,
) -> dict:
    """Build a complete extraction dict for validation testing."""
    if charges is None:
        charges = [
            make_charge("L001", "energy", 98.20, 1000, 0.0982, "supply"),
            make_charge("L002", "rider", 67.15, 750, 0.08953, "distribution"),
            make_charge("L003", "tax", 22.10, None, None, "taxes"),
        ]
    if meters is None:
        meters = [make_meter()]

    return {
        "extraction_metadata": {
            "source_document": {"image_quality_score": 0.9, "ocr_applied": False},
            "locale_context": None,
        },
        "classification": {
            "commodity_type": commodity,
            "has_demand_charges": False,
            "has_tou": False,
            "has_supplier_split": False,
        },
        "invoice": {
            "billing_period": {"days": 30},
        },
        "account": {},
        "meters": meters,
        "charges": charges,
        "totals": {
            "supply_subtotal": {"value": 98.20},
            "distribution_subtotal": {"value": 67.15},
            "taxes_subtotal": {"value": 22.10},
            "current_charges": {"value": current_charges},
            "total_amount_due": {"value": total_amount},
            "minimum_bill_applied": False,
        },
    }
