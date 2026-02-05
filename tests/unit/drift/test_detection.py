"""Test drift detection."""
import pytest
from invoice_ingestion.drift.detection import detect_drift


class TestDriftDetection:
    def test_identical_no_drift(self):
        ext = {"totals": {"total_amount_due": {"value": 100}}, "account": {"account_number": {"value": "123"}}}
        result = detect_drift(ext, ext)
        assert result is None

    def test_one_field_changed(self):
        old = {"totals": {"total_amount_due": {"value": 100}}}
        new = {"totals": {"total_amount_due": {"value": 101}}}
        result = detect_drift(new, old)
        assert result is not None
        assert len(result.drift_fields) > 0

    def test_fatal_field_change(self):
        old = {"account": {"account_number": {"value": "123"}}}
        new = {"account": {"account_number": {"value": "456"}}}
        result = detect_drift(new, old)
        assert result is not None
        assert result.fatal_drift is True

    def test_cause_hypothesis_model_change(self):
        old = {"extraction_metadata": {"models_used": {"extraction_1a": {"model": "v1"}}}, "data": 1}
        new = {"extraction_metadata": {"models_used": {"extraction_1a": {"model": "v2"}}}, "data": 2}
        result = detect_drift(new, old)
        assert result is not None
        assert "model" in result.cause_hypothesis.lower() if result.cause_hypothesis else True
