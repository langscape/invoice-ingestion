"""Test ExtractionResult schema serialization and round-trip."""
import pytest
import json
from invoice_ingestion.models.schema import (
    ExtractionResult, ConfidentValue, MonetaryAmount,
    CommodityType, ComplexityTier, ConfidenceTier,
    ChargeCategory, ChargeOwner, ChargeSection,
    MathDisposition, VATCategory, MarketModel,
)


class TestConfidentValue:
    def test_construct(self):
        cv = ConfidentValue[str](value="test", confidence=0.95)
        assert cv.value == "test"
        assert cv.confidence == 0.95

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ConfidentValue[str](value="x", confidence=1.5)
        with pytest.raises(Exception):
            ConfidentValue[str](value="x", confidence=-0.1)

    def test_optional_source(self):
        cv = ConfidentValue[str](value="test", confidence=0.9, source_location="page1:top")
        assert cv.source_location == "page1:top"
        cv2 = ConfidentValue[str](value="test", confidence=0.9)
        assert cv2.source_location is None


class TestMonetaryAmount:
    def test_construct(self):
        ma = MonetaryAmount(value=23.66, currency="EUR", original_string="23,66 \u20ac")
        assert ma.value == 23.66
        assert ma.currency == "EUR"
        assert ma.original_string == "23,66 \u20ac"

    def test_default_currency(self):
        ma = MonetaryAmount(value=10.0)
        assert ma.currency == "USD"


class TestEnums:
    def test_commodity_type_values(self):
        assert CommodityType.NATURAL_GAS == "natural_gas"
        assert CommodityType.ELECTRICITY == "electricity"
        assert CommodityType.WATER == "water"

    def test_complexity_tier_values(self):
        assert ComplexityTier.SIMPLE == "simple"
        assert ComplexityTier.PATHOLOGICAL == "pathological"

    def test_charge_category_values(self):
        assert len(ChargeCategory) == 10
        assert ChargeCategory.ENERGY == "energy"
        assert ChargeCategory.CREDIT == "credit"

    def test_math_disposition_values(self):
        assert MathDisposition.CLEAN == "clean"
        assert MathDisposition.DISCREPANCY == "discrepancy"

    def test_enum_serialization(self):
        assert str(CommodityType.ELECTRICITY) == "electricity"
