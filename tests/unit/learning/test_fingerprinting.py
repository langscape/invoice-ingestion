"""Test format fingerprinting."""
import pytest
from invoice_ingestion.learning.fingerprinting import FingerprintLibrary


class TestFingerprintLibrary:
    def test_match_by_utility(self):
        lib = FingerprintLibrary()
        lib.create("ConEd", "electricity", {"header": "ConEdison"})
        result = lib.match("ConEd", "electricity")
        assert result is not None
        assert result.utility == "ConEd"

    def test_no_match(self):
        lib = FingerprintLibrary()
        assert lib.match("Unknown", "electricity") is None

    def test_create_new(self):
        lib = FingerprintLibrary()
        fp = lib.create("TestUtil", "gas", {"pattern": "test"})
        assert fp.invoices_processed == 0

    def test_update_accuracy(self):
        lib = FingerprintLibrary()
        fp = lib.create("TestUtil", "gas", {"pattern": "test"})
        lib.update_accuracy(fp, True)
        lib.update_accuracy(fp, True)
        lib.update_accuracy(fp, False)
        assert fp.accuracy == pytest.approx(2/3)
        assert fp.invoices_processed == 3

    def test_should_create_new(self):
        lib = FingerprintLibrary()
        assert lib.should_create_new("NewUtil", 3) is True
        assert lib.should_create_new("NewUtil", 2) is False
