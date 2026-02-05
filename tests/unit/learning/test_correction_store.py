"""Test correction store."""
import pytest
from invoice_ingestion.learning.correction_store import CorrectionStore, CorrectionEntry


class TestCorrectionStore:
    def test_store_and_query(self):
        store = CorrectionStore()
        entry = CorrectionEntry("charges.L001.amount", "23.66", "23.67", "value_change", utility="ConEd", commodity="electricity")
        store.store(entry)
        results = store.query(utility="ConEd")
        assert len(results) == 1

    def test_query_by_commodity(self):
        store = CorrectionStore()
        store.store(CorrectionEntry("f1", "a", "b", "t", commodity="electricity"))
        store.store(CorrectionEntry("f2", "a", "b", "t", commodity="gas"))
        assert len(store.query(commodity="electricity")) == 1

    def test_min_recurrence_filter(self):
        store = CorrectionStore()
        store.store(CorrectionEntry("field_a", "1", "2", "t"))
        store.store(CorrectionEntry("field_a", "3", "4", "t"))
        store.store(CorrectionEntry("field_b", "5", "6", "t"))
        results = store.query(min_recurrence=2)
        assert len(results) == 2  # Both field_a entries
        assert all(r.field_path == "field_a" for r in results)

    def test_group_by_pattern(self):
        store = CorrectionStore()
        store.store(CorrectionEntry("field_a", "1", "2", "t"))
        store.store(CorrectionEntry("field_a", "3", "4", "t"))
        store.store(CorrectionEntry("field_b", "5", "6", "t"))
        groups = store.group_by_pattern()
        assert len(groups) == 2
        assert groups[0]["field_path"] == "field_a"
        assert groups[0]["count"] == 2
