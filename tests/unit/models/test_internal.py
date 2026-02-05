"""Test inter-pass data models."""
import pytest
from invoice_ingestion.models.internal import (
    PageData, IngestionResult, ClassificationResult,
    Pass1AResult, Pass1BResult, Pass2Result, Pass3Result, Pass4Result,
    ValidationIssue, AuditQuestion,
)
from tests.factories import make_page_data, make_ingestion_result, make_classification


class TestPageData:
    def test_construct(self):
        pd = make_page_data(1, 0.9, "en")
        assert pd.page_number == 1
        assert pd.quality_score == 0.9

class TestIngestionResult:
    def test_construct(self):
        ir = make_ingestion_result(pages=3, quality=0.8)
        assert len(ir.pages) == 3
        assert ir.image_quality_score == 0.8
        assert ir.file_type == "pdf"

class TestClassificationResult:
    def test_construct(self):
        cr = make_classification(commodity="natural_gas", tier="complex")
        assert cr.commodity_type == "natural_gas"
        assert cr.complexity_tier == "complex"

class TestPass1AResult:
    def test_construct(self):
        r = Pass1AResult(invoice={"number": "123"}, account={"id": "A1"}, meters=[])
        assert r.invoice["number"] == "123"

class TestPass3Result:
    def test_construct(self):
        r = Pass3Result(issues=[], math_disposition="clean")
        assert len(r.issues) == 0

    def test_with_issues(self):
        issues = [ValidationIssue(field="test", severity="warning", message="test msg")]
        r = Pass3Result(issues=issues, math_disposition="rounding_variance")
        assert len(r.issues) == 1
