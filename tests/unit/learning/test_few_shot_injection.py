"""Test few-shot context building."""
import pytest
from invoice_ingestion.learning.correction_store import CorrectionStore, CorrectionEntry
from invoice_ingestion.learning.few_shot_injection import get_few_shot_context


class TestFewShotInjection:
    def test_no_corrections_empty(self):
        store = CorrectionStore()
        result = get_few_shot_context(store)
        assert result == ""

    def test_single_correction_below_threshold(self):
        store = CorrectionStore()
        store.store(CorrectionEntry("field_a", "1", "2", "t"))
        result = get_few_shot_context(store, min_recurrence=2)
        assert result == ""

    def test_two_corrections_meets_threshold(self):
        store = CorrectionStore()
        store.store(CorrectionEntry("field_a", "1", "2", "t", reason="off by one"))
        store.store(CorrectionEntry("field_a", "3", "4", "t", reason="off by one"))
        result = get_few_shot_context(store, min_recurrence=2)
        assert "KNOWN ISSUES" in result
        assert "field_a" in result

    def test_format_includes_examples(self):
        store = CorrectionStore()
        for i in range(3):
            store.store(CorrectionEntry("charges.amount", str(i), str(i+1), "t"))
        result = get_few_shot_context(store, min_recurrence=2)
        assert "Extracted:" in result
        assert "Corrected:" in result
