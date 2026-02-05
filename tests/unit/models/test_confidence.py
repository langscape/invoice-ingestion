"""Test confidence scoring, thresholds, and fatal triggers."""
import pytest
from invoice_ingestion.models.confidence import compute_confidence, determine_tier
from invoice_ingestion.models.schema import ComplexityTier, ConfidenceTier
from invoice_ingestion.models.internal import ValidationIssue


class TestComputeConfidence:
    def test_clean_extraction(self):
        result = compute_confidence(
            extraction={
                "extraction_metadata": {"source_document": {"image_quality_score": 0.9, "ocr_applied": False}},
                "classification": {"complexity_tier": "simple"},
            },
            validation={},
            audit={},
        )
        assert result.score >= 0.95

    def test_fatal_field_error(self):
        result = compute_confidence(
            extraction={
                "extraction_metadata": {"source_document": {"image_quality_score": 0.9, "ocr_applied": False}},
                "classification": {"complexity_tier": "simple"},
            },
            validation={
                "line_dispositions": [
                    {"field": "total_amount_due", "disposition": "discrepancy"},
                ],
            },
            audit={},
        )
        assert result.score < 0.5
        assert result.fatal_triggered is True

    def test_rounding_variance_no_penalty(self):
        result = compute_confidence(
            extraction={
                "extraction_metadata": {"source_document": {"image_quality_score": 0.9, "ocr_applied": False}},
                "classification": {"complexity_tier": "simple"},
            },
            validation={
                "line_dispositions": [
                    {"field": "charges.L001.amount", "disposition": "rounding_variance"},
                ],
            },
            audit={},
        )
        assert result.score >= 0.90

    def test_ocr_penalty(self):
        result_no_ocr = compute_confidence(
            extraction={
                "extraction_metadata": {"source_document": {"image_quality_score": 0.9, "ocr_applied": False}},
                "classification": {"complexity_tier": "simple"},
            },
            validation={},
            audit={},
        )
        result_ocr = compute_confidence(
            extraction={
                "extraction_metadata": {"source_document": {"image_quality_score": 0.9, "ocr_applied": True}},
                "classification": {"complexity_tier": "simple"},
            },
            validation={},
            audit={},
        )
        assert result_no_ocr.score > result_ocr.score

    def test_low_quality_penalty(self):
        result_good = compute_confidence(
            extraction={
                "extraction_metadata": {"source_document": {"image_quality_score": 0.9, "ocr_applied": False}},
                "classification": {"complexity_tier": "simple"},
            },
            validation={},
            audit={},
        )
        result_bad = compute_confidence(
            extraction={
                "extraction_metadata": {"source_document": {"image_quality_score": 0.3, "ocr_applied": False}},
                "classification": {"complexity_tier": "simple"},
            },
            validation={},
            audit={},
        )
        assert result_good.score > result_bad.score


class TestDetermineTier:
    def test_fatal_always_full_review(self):
        assert determine_tier(0.99, fatal_triggered=True, complexity=ComplexityTier.SIMPLE) == ConfidenceTier.FULL_REVIEW

    def test_simple_auto_accept(self):
        assert determine_tier(0.96, fatal_triggered=False, complexity=ComplexityTier.SIMPLE) == ConfidenceTier.AUTO_ACCEPT

    def test_simple_targeted_review(self):
        assert determine_tier(0.85, fatal_triggered=False, complexity=ComplexityTier.SIMPLE) == ConfidenceTier.TARGETED_REVIEW

    def test_simple_full_review(self):
        assert determine_tier(0.60, fatal_triggered=False, complexity=ComplexityTier.SIMPLE) == ConfidenceTier.FULL_REVIEW

    def test_complex_auto_accept(self):
        assert determine_tier(0.92, fatal_triggered=False, complexity=ComplexityTier.COMPLEX) == ConfidenceTier.AUTO_ACCEPT

    def test_complex_targeted_review(self):
        assert determine_tier(0.80, fatal_triggered=False, complexity=ComplexityTier.COMPLEX) == ConfidenceTier.TARGETED_REVIEW

    def test_complex_full_review(self):
        assert determine_tier(0.50, fatal_triggered=False, complexity=ComplexityTier.COMPLEX) == ConfidenceTier.FULL_REVIEW
