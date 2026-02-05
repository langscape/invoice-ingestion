"""Test classify_complexity() edge cases."""
import pytest
from invoice_ingestion.models.classification import classify_complexity


class TestClassifyComplexity:
    def test_simple_invoice(self):
        tier = classify_complexity(signals=[], line_item_count=5, page_count=1)
        assert tier == "simple"

    def test_simple_with_one_medium_signal(self):
        tier = classify_complexity(signals=["tiered_rates"], line_item_count=8, page_count=2)
        assert tier == "simple"

    def test_standard_multiple_medium(self):
        tier = classify_complexity(signals=["tou_present", "demand_charges", "supplier_split"],
                                    line_item_count=12, page_count=3)
        assert tier == "standard"

    def test_complex_with_high_signal(self):
        tier = classify_complexity(signals=["multi_meter", "tou_present", "demand_charges"],
                                    line_item_count=20, page_count=4)
        assert tier == "complex"

    def test_pathological(self):
        tier = classify_complexity(
            signals=["multi_meter", "net_metering", "prior_period_adjustments", "tou_present", "demand_charges"],
            line_item_count=40, page_count=8)
        assert tier == "pathological"

    def test_high_line_count_bumps(self):
        tier = classify_complexity(signals=["tou_present"], line_item_count=35, page_count=2)
        assert tier in ("standard", "complex")

    def test_eu_vat_adds_complexity(self):
        tier = classify_complexity(
            signals=["tou_present"], line_item_count=15, page_count=3,
            has_multiple_vat_rates=True, has_calorific_conversion=True)
        assert tier in ("standard", "complex")

    def test_page_count_bonus(self):
        tier_short = classify_complexity(signals=[], line_item_count=10, page_count=2)
        tier_long = classify_complexity(signals=[], line_item_count=10, page_count=7)
        # More pages should increase or equal complexity
        assert _complexity_tier_to_int(tier_long) >= _complexity_tier_to_int(tier_short)


def _complexity_tier_to_int(tier: str) -> int:
    return {"simple": 0, "standard": 1, "complex": 2, "pathological": 3}[tier]
