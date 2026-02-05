"""Test audit question builder and comparison."""
import pytest
from invoice_ingestion.passes.pass4_audit import build_audit_questions, compare_audit
from tests.factories import make_classification


class TestBuildAuditQuestions:
    def test_base_questions_always_present(self):
        cls = make_classification()
        questions = build_audit_questions(cls)
        assert len(questions) >= 5
        assert any("total amount due" in q.question.lower() for q in questions)
        assert any("account number" in q.question.lower() for q in questions)

    def test_demand_questions_when_has_demand(self):
        cls = make_classification(has_demand=True)
        questions = build_audit_questions(cls)
        assert any("demand" in q.question.lower() for q in questions)

    def test_tou_questions_when_has_tou(self):
        cls = make_classification(has_tou=True)
        questions = build_audit_questions(cls)
        assert any("time-of-use" in q.question.lower() for q in questions)

    def test_supplier_questions_when_split(self):
        cls = make_classification(has_supplier_split=True)
        questions = build_audit_questions(cls)
        assert any("supplier" in q.question.lower() for q in questions)

    def test_water_specific(self):
        cls = make_classification(commodity="water")
        questions = build_audit_questions(cls)
        assert any("water" in q.question.lower() and "sewer" in q.question.lower() for q in questions)

    def test_complex_gets_extra_questions(self):
        simple_cls = make_classification(tier="simple")
        complex_cls = make_classification(tier="complex")
        simple_q = build_audit_questions(simple_cls)
        complex_q = build_audit_questions(complex_cls)
        assert len(complex_q) > len(simple_q)

    def test_vat_questions_for_eu(self):
        cls = make_classification()
        locale = {"tax_regime": "eu_vat", "country_code": "DE"}
        questions = build_audit_questions(cls, locale_context=locale)
        assert any("vat" in q.question.lower() for q in questions)


class TestCompareAudit:
    def test_total_match(self):
        extraction = {"totals": {"total_amount_due": {"value": 187.45}}, "meters": [], "account": {"account_number": {"value": "123"}}}
        audit = {"total_amount_due": "$187.45"}
        mismatches = compare_audit(extraction, audit)
        assert len(mismatches) == 0

    def test_total_mismatch(self):
        extraction = {"totals": {"total_amount_due": {"value": 187.45}}, "meters": [], "account": {"account_number": {"value": "123"}}}
        audit = {"total_amount_due": "$250.00"}
        mismatches = compare_audit(extraction, audit)
        assert any(m["severity"] == "fatal" for m in mismatches)
