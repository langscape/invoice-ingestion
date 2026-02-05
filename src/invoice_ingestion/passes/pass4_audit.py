"""Pass 4: Conditional Audit -- cross-verification with different model."""
from __future__ import annotations
import re
import structlog
from ..llm.base import LLMClient
from ..llm.response_parser import extract_json_from_response
from ..models.internal import IngestionResult, ClassificationResult, Pass4Result, AuditQuestion
from ..prompts.registry import PromptRegistry

logger = structlog.get_logger(__name__)

BASE_QUESTIONS = [
    AuditQuestion(question="What is the total amount due on this invoice?", field_to_check="totals.total_amount_due"),
    AuditQuestion(question="What is the billing period (start and end dates)?", field_to_check="invoice.billing_period"),
    AuditQuestion(question="What is the account number?", field_to_check="account.account_number"),
    AuditQuestion(question="What is the total consumption shown, and in what units?", field_to_check="meters.consumption"),
    AuditQuestion(question="How many meters are listed?", field_to_check="meters.count"),
]


def build_audit_questions(classification: ClassificationResult, locale_context: dict | None = None) -> list[AuditQuestion]:
    """Build conditional audit questions based on classification."""
    questions = list(BASE_QUESTIONS)

    if classification.has_demand_charges:
        questions.append(AuditQuestion(
            question="Is there a demand charge (kW or kVA)? If so, what is the demand value and the demand charge amount?",
            field_to_check="meters.demand",
        ))

    if classification.has_tou:
        questions.append(AuditQuestion(
            question="Are there time-of-use rate tiers? If so, list each tier name and its consumption amount.",
            field_to_check="meters.tou_breakdown",
        ))

    if classification.has_supplier_split:
        questions.append(AuditQuestion(
            question="Are charges split between a utility/distribution company and a separate supplier? If so, name both entities and their respective subtotals.",
            field_to_check="account.supplier",
        ))

    if classification.has_net_metering:
        questions.append(AuditQuestion(
            question="Is there solar generation, net metering, or export credits shown? If so, what are the generation, export, and net values?",
            field_to_check="meters.generation",
        ))

    if classification.has_prior_period_adjustments:
        questions.append(AuditQuestion(
            question="Are there any charges labeled as adjustments, true-ups, or corrections for a prior period? If so, what period do they reference?",
            field_to_check="charges.prior_period",
        ))

    if classification.commodity_type == "electricity":
        questions.append(AuditQuestion(
            question="Are there any capacity charges (ICAP, PLC, transmission) that reference a different period than the billing period?",
            field_to_check="charges.capacity",
        ))

    if classification.commodity_type == "water":
        questions.append(AuditQuestion(
            question="Are water and sewer charges shown separately? What are the respective totals?",
            field_to_check="totals.water_sewer",
        ))

    if classification.complexity_tier in ("complex", "pathological"):
        questions.append(AuditQuestion(
            question="Are there any charges that appear to use a minimum bill or take-or-pay calculation?",
            field_to_check="totals.minimum_bill",
        ))
        questions.append(AuditQuestion(
            question="Do any line items show a quantity x rate that does NOT equal the stated amount?",
            field_to_check="charges.math_check",
        ))

    # International additions
    if locale_context:
        tax_regime = locale_context.get("tax_regime", "")
        if "vat" in tax_regime or "iva" in tax_regime:
            questions.append(AuditQuestion(
                question="What are the VAT rates applied and the total VAT amount?",
                field_to_check="totals.vat_summary",
            ))

        country = locale_context.get("country_code", "")
        if country == "DE":
            questions.append(AuditQuestion(
                question="Is there a Brennwert (calorific value) and Zustandszahl (volume correction factor) shown?",
                field_to_check="meters.conversion_factors",
            ))
        if country in ("FR", "ES"):
            questions.append(AuditQuestion(
                question="Is there a contracted power (puissance souscrite / potencia contratada) shown?",
                field_to_check="meters.contracted_capacity",
            ))

    return questions


def compare_audit(extraction: dict, audit_answers: dict) -> list[dict]:
    """Compare audit answers to extraction values. Returns list of mismatches."""
    mismatches: list[dict] = []

    # Total amount due
    audit_total = _parse_number(audit_answers.get("total_amount_due", ""))
    extraction_total = _nested_get(extraction, "totals.total_amount_due.value")
    if audit_total is not None and extraction_total is not None:
        if abs(audit_total - extraction_total) > 0.50:
            mismatches.append({
                "field": "total_amount_due",
                "extraction_value": extraction_total,
                "audit_value": audit_total,
                "severity": "fatal",
            })

    # Meter count
    audit_meters = _parse_number(audit_answers.get("meter_count", ""))
    extraction_meters = len(extraction.get("meters", []))
    if audit_meters is not None and int(audit_meters) != extraction_meters:
        mismatches.append({
            "field": "meter_count",
            "extraction_value": extraction_meters,
            "audit_value": int(audit_meters),
            "severity": "high",
        })

    # Account number
    audit_acct = audit_answers.get("account_number", "").strip()
    extraction_acct = _nested_get(extraction, "account.account_number.value")
    if audit_acct and extraction_acct and audit_acct != str(extraction_acct):
        mismatches.append({
            "field": "account_number",
            "extraction_value": extraction_acct,
            "audit_value": audit_acct,
            "severity": "fatal",
        })

    return mismatches


async def run_pass4(
    ingestion: IngestionResult,
    classification: ClassificationResult,
    extraction: dict,
    audit_llm: LLMClient,
    prompt_registry: PromptRegistry,
    locale_context: dict | None = None,
) -> Pass4Result:
    """Run audit pass with different LLM."""
    questions = build_audit_questions(classification, locale_context)

    # Format questions for prompt
    questions_text = "\n".join(f"{i+1}. {q.question}" for i, q in enumerate(questions))

    images = [p.image_base64 for p in ingestion.pages]

    prompt = prompt_registry.render("audit", variables={"questions": questions_text})

    response = await audit_llm.complete_vision(
        system_prompt="You are an independent invoice verification specialist. Answer each question based ONLY on what you see in the invoice images. Do NOT guess.",
        user_prompt=prompt,
        images=images,
        temperature=0.0,
        max_tokens=4096,
    )

    answers = extract_json_from_response(response.content)

    # Fill in answers
    for q in questions:
        q.answer = answers.get(q.field_to_check, answers.get(q.question, ""))

    # Compare with extraction
    mismatches = compare_audit(extraction, answers)

    return Pass4Result(
        questions_asked=questions,
        fields_checked=len(questions),
        fields_matched=len(questions) - len(mismatches),
        mismatches=mismatches,
        audit_model=audit_llm.get_model_name(),
    )


def _parse_number(s: str) -> float | None:
    if not s:
        return None
    nums = re.findall(r'[\d,]+\.?\d*', s.replace(',', ''))
    if nums:
        try:
            return float(nums[0])
        except ValueError:
            return None
    return None


def _nested_get(d: dict, path: str):
    keys = path.split(".")
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return None
    return d
