"""Pipeline orchestrator: Pass 0 → 0.5 → 1A → 1B → 2 → 3 → 4 → confidence gate."""
from __future__ import annotations
import time
import structlog
from datetime import datetime, timezone
from uuid import uuid4

from .config import Settings
from .llm.base import LLMClient
from .llm.anthropic_client import AnthropicClient
from .llm.openai_client import OpenAIClient
from .llm.failover import FailoverLLMClient
from .llm.response_parser import extract_json_from_response
from .prompts.registry import PromptRegistry
from .models.schema import (
    ExtractionResult, ExtractionMetadata, Classification, Invoice, Account,
    Meter, Charge, Totals, Validation, MathResults, ConsumptionCrosschecks,
    LogicChecks, AuditResults, TraceabilityEntry, BoundedVarianceRecord,
    SourceDocument, ModelInfo, ConfidenceTier, LocaleContext, CurrencyInfo,
    MonetaryAmount, ConfidentValue, MathDisposition,
)
from .models.internal import IngestionResult, ClassificationResult
from .models.confidence import compute_confidence, determine_tier
from .passes.pass0_ingestion import run_pass0
from .passes.pass05_classification import run_pass05
from .passes.pass1a_extraction import run_pass1a
from .passes.pass1b_extraction import run_pass1b
from .passes.pass2_schema_mapping import run_pass2
from .passes.pass3_validation import run_pass3
from .passes.pass4_audit import run_pass4
from .learning.correction_store import CorrectionStore
from .learning.few_shot_injection import get_few_shot_context
from .learning.fingerprinting import FingerprintLibrary
from .drift.detection import detect_drift
from .international.locale_detection import detect_locale
from .utils.hashing import compute_string_hash

logger = structlog.get_logger(__name__)


class ExtractionPipeline:
    """Orchestrates the full extraction pipeline."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.prompt_registry = PromptRegistry()
        self.correction_store = CorrectionStore()
        self.fingerprint_library = FingerprintLibrary()

        # Initialize LLM clients
        self._init_llm_clients()

    def _init_llm_clients(self):
        """Initialize LLM clients — all models deployed via Azure."""
        azure_ai_key = self.settings.azure_ai_api_key.get_secret_value()
        azure_ai_endpoint = self.settings.azure_ai_endpoint
        azure_openai_key = self.settings.azure_openai_api_key.get_secret_value()
        azure_openai_endpoint = self.settings.azure_openai_endpoint

        # Claude models via Azure AI Foundry
        self._classification_client: LLMClient = AnthropicClient(
            api_key=azure_ai_key,
            model=self.settings.classification_model,
            azure_endpoint=azure_ai_endpoint,
        )

        extraction_primary: LLMClient = AnthropicClient(
            api_key=azure_ai_key,
            model=self.settings.extraction_model,
            azure_endpoint=azure_ai_endpoint,
        )

        # Failover: Claude (Azure AI) → GPT-4o (Azure OpenAI)
        if self.settings.enable_failover and azure_openai_key:
            extraction_fallback = OpenAIClient(
                api_key=azure_openai_key,
                model="gpt-4o",
                azure_endpoint=azure_openai_endpoint,
            )
            self._extraction_client = FailoverLLMClient(extraction_primary, extraction_fallback)
        else:
            self._extraction_client = extraction_primary

        self._schema_mapping_client: LLMClient = AnthropicClient(
            api_key=azure_ai_key,
            model=self.settings.schema_mapping_model,
            azure_endpoint=azure_ai_endpoint,
        )

        # Audit: always different provider — GPT-4o via Azure OpenAI
        self._audit_client: LLMClient = OpenAIClient(
            api_key=azure_openai_key,
            model=self.settings.audit_model,
            azure_endpoint=azure_openai_endpoint,
        )

    async def process(self, file_bytes: bytes, blob_name: str) -> ExtractionResult:
        """Run the full extraction pipeline."""
        start_time = time.monotonic()
        extraction_id = uuid4()
        flags: list[str] = []

        logger.info("pipeline_start", extraction_id=str(extraction_id), blob_name=blob_name)

        # --- Pass 0: Ingestion ---
        try:
            ingestion = run_pass0(file_bytes, dpi=self.settings.dpi)
        except Exception as e:
            logger.error("pass0_failed", error=str(e))
            raise

        # --- Pass 0.5: Classification ---
        try:
            # Get few-shot context if learning loop enabled
            few_shot = ""
            if self.settings.enable_learning_loop:
                few_shot = get_few_shot_context(self.correction_store)

            classification = await run_pass05(
                ingestion, self._classification_client, self.prompt_registry,
                few_shot_context=few_shot or None,
            )
        except Exception as e:
            logger.error("pass05_failed", error=str(e))
            flags.append("classification_failed")
            # Use defaults
            classification = ClassificationResult(
                commodity_type="electricity", commodity_confidence=0.0,
                complexity_tier="standard", complexity_signals=[],
                market_type="unknown",
            )

        # Detect locale
        all_text = " ".join(p.extracted_text or "" for p in ingestion.pages)
        locale_info = detect_locale(all_text, language=classification.language)

        # Build few-shot for extraction passes
        few_shot_extraction = ""
        if self.settings.enable_learning_loop:
            utility_name = None  # will be filled after pass 1a
            few_shot_extraction = get_few_shot_context(
                self.correction_store,
                commodity=classification.commodity_type,
            )
        few_shot_hash = compute_string_hash(few_shot_extraction) if few_shot_extraction else None

        # --- Pass 1A: Structure & Metering ---
        try:
            pass1a = await run_pass1a(
                ingestion, classification, self._extraction_client, self.prompt_registry,
                few_shot_context=few_shot_extraction or None,
            )
        except Exception as e:
            logger.error("pass1a_failed", error=str(e))
            flags.append("pass1a_failed")
            pass1a = None

        # --- Pass 1B: Charges & Financial ---
        try:
            pass1b = await run_pass1b(
                ingestion, classification, pass1a, self._extraction_client, self.prompt_registry,
                few_shot_context=few_shot_extraction or None,
            )
        except Exception as e:
            logger.error("pass1b_failed", error=str(e))
            flags.append("pass1b_failed")
            pass1b = None

        # --- Pass 2: Schema Mapping ---
        try:
            pass2 = await run_pass2(
                classification, pass1a, pass1b, self._schema_mapping_client, self.prompt_registry,
            )
            merged_data = pass2.data
        except Exception as e:
            logger.error("pass2_failed", error=str(e))
            flags.append("pass2_failed")
            merged_data = {}

        # --- Pass 3: Validation ---
        try:
            pass3 = run_pass3(merged_data, country_code=locale_info.get("country_code"))
            for issue in pass3.issues:
                if issue.severity == "fatal":
                    flags.append(f"fatal:{issue.field}")
        except Exception as e:
            logger.error("pass3_failed", error=str(e))
            flags.append("pass3_failed")
            pass3 = None

        # --- Pass 4: Audit ---
        try:
            pass4 = await run_pass4(
                ingestion, classification, merged_data, self._audit_client,
                self.prompt_registry, locale_context=locale_info,
            )
        except Exception as e:
            logger.error("pass4_failed", error=str(e))
            flags.append("pass4_failed")
            pass4 = None

        # --- Confidence Gate ---
        validation_issues = pass3.issues if pass3 else []
        audit_mismatches = pass4.mismatches if pass4 else []

        confidence_result = compute_confidence(
            extraction=merged_data,
            validation={"math_results": {}, "line_dispositions": []},
            audit={"mismatches": audit_mismatches},
        )

        confidence_score = confidence_result.score
        confidence_tier = confidence_result.tier

        # --- Assemble result ---
        processing_time = int((time.monotonic() - start_time) * 1000)

        result = self._assemble_result(
            extraction_id=extraction_id,
            ingestion=ingestion,
            classification=classification,
            merged_data=merged_data,
            pass3=pass3,
            pass4=pass4,
            locale_info=locale_info,
            confidence_score=confidence_score,
            confidence_tier=confidence_tier,
            flags=flags,
            processing_time=processing_time,
            few_shot_hash=few_shot_hash,
        )

        logger.info("pipeline_complete", extraction_id=str(extraction_id),
                    confidence=confidence_score, tier=confidence_tier,
                    processing_time_ms=processing_time)

        return result

    def _assemble_result(self, extraction_id, ingestion, classification, merged_data,
                         pass3, pass4, locale_info, confidence_score, confidence_tier,
                         flags, processing_time, few_shot_hash) -> ExtractionResult:
        """Assemble the final ExtractionResult from pipeline outputs."""

        # Build metadata
        locale_context = LocaleContext(
            country_code=locale_info.get("country_code"),
            country_name=None,
            language=locale_info.get("language", "en"),
            currency=CurrencyInfo(
                code=locale_info.get("currency_code", "USD"),
                symbol=locale_info.get("currency_symbol", "$"),
                decimal_separator=locale_info.get("decimal_separator", "."),
                thousands_separator=locale_info.get("thousands_separator", ","),
            ),
            date_format_detected=locale_info.get("date_format"),
            number_format_detected=locale_info.get("number_format"),
            tax_regime=locale_info.get("tax_regime"),
            market_model=locale_info.get("market_model", "regulated"),
        ) if locale_info else None

        metadata = ExtractionMetadata(
            extraction_id=extraction_id,
            extraction_timestamp=datetime.now(timezone.utc),
            pipeline_version="v0.1.0",
            models_used={
                "classification": ModelInfo(model=self.settings.classification_model, temperature=0.0),
                "extraction_1a": ModelInfo(model=self.settings.extraction_model, temperature=0.0),
                "extraction_1b": ModelInfo(model=self.settings.extraction_model, temperature=0.0),
                "schema_mapping": ModelInfo(model=self.settings.schema_mapping_model, temperature=0.0),
                "audit": ModelInfo(model=self.settings.audit_model, temperature=0.0),
            },
            prompt_versions={
                "classification": self.prompt_registry.get_version("classification"),
                "extraction_1a": self.prompt_registry.get_version("extraction_1a"),
                "extraction_1b": self.prompt_registry.get_version("extraction_1b"),
                "schema_mapping": self.prompt_registry.get_version("schema_mapping"),
                "audit": self.prompt_registry.get_version("audit"),
            },
            few_shot_context_hash=few_shot_hash,
            overall_confidence=confidence_score,
            confidence_tier=ConfidenceTier(confidence_tier),
            flags=flags,
            processing_time_ms=processing_time,
            source_document=SourceDocument(
                file_hash=ingestion.file_hash,
                file_type=ingestion.file_type,
                page_count=len(ingestion.pages),
                pages_used=list(range(1, len(ingestion.pages) + 1)),
                pages_discarded=[],
                ocr_applied=False,
                image_quality_score=ingestion.image_quality_score,
                language_detected=ingestion.language_detected,
                language_translated=ingestion.language_detected != "en",
            ),
            locale_context=locale_context,
        )

        # Build classification model
        cls = Classification(
            commodity_type=classification.commodity_type,
            commodity_confidence=classification.commodity_confidence,
            complexity_tier=classification.complexity_tier,
            complexity_signals=classification.complexity_signals,
            market_type=classification.market_type,
            has_supplier_split=classification.has_supplier_split,
            has_demand_charges=classification.has_demand_charges,
            has_tou=classification.has_tou,
            has_net_metering=classification.has_net_metering,
            has_prior_period_adjustments=classification.has_prior_period_adjustments,
            estimated_line_item_count=classification.estimated_line_item_count,
            format_fingerprint=classification.format_fingerprint,
            has_multiple_vat_rates=classification.has_multiple_vat_rates,
            has_calorific_conversion=classification.has_calorific_conversion,
            has_contracted_capacity=classification.has_contracted_capacity,
        )

        # Build invoice, account, meters, charges, totals from merged_data
        # Use merged_data dict with defaults for missing fields
        invoice_data = merged_data.get("invoice", {})
        invoice = Invoice(
            invoice_number=ConfidentValue(value=invoice_data.get("invoice_number", {}).get("value", ""), confidence=invoice_data.get("invoice_number", {}).get("confidence", 0.0)),
            invoice_date=ConfidentValue(value=invoice_data.get("invoice_date", {}).get("value", ""), confidence=invoice_data.get("invoice_date", {}).get("confidence", 0.0)),
            due_date=ConfidentValue(value=invoice_data.get("due_date", {}).get("value", ""), confidence=invoice_data.get("due_date", {}).get("confidence", 0.0)),
            billing_period=invoice_data.get("billing_period"),
            rate_schedule=ConfidentValue(value=invoice_data.get("rate_schedule", {}).get("value"), confidence=invoice_data.get("rate_schedule", {}).get("confidence", 0.0)) if invoice_data.get("rate_schedule") else None,
            statement_type=invoice_data.get("statement_type", "regular"),
        )

        account_data = merged_data.get("account", {})
        account = Account(
            account_number=ConfidentValue(value=account_data.get("account_number", {}).get("value", ""), confidence=account_data.get("account_number", {}).get("confidence", 0.0)),
            customer_name=ConfidentValue(value=account_data.get("customer_name", {}).get("value", ""), confidence=account_data.get("customer_name", {}).get("confidence", 0.0)),
            service_address=ConfidentValue(value=account_data.get("service_address", {}).get("value", ""), confidence=account_data.get("service_address", {}).get("confidence", 0.0)),
            utility_provider=ConfidentValue(value=account_data.get("utility_provider", {}).get("value", ""), confidence=account_data.get("utility_provider", {}).get("confidence", 0.0)),
        )

        # Build validation
        validation = None
        if pass3:
            math_issues = [i for i in pass3.issues if "math" in i.field or "total" in i.field]
            validation = Validation(
                math_results=MathResults(
                    line_items_sum=0.0,
                    stated_current_charges=0.0,
                    difference=0.0,
                    line_items_sum_valid=not any(i.severity in ("fatal", "warning") for i in math_issues),
                    section_subtotals_valid=True,
                    account_balance_valid=True,
                    notes=[i.message for i in pass3.issues],
                ),
                utility_math_adjustments=[],
                consumption_crosschecks=ConsumptionCrosschecks(
                    meter_reads_match_consumption=not any("consumption" in i.field for i in pass3.issues if i.severity == "warning"),
                    tou_sums_to_total=not any("tou" in i.field for i in pass3.issues if i.severity == "warning"),
                    notes=[],
                ),
                logic_checks=LogicChecks(
                    commodity_unit_consistency=not any("commodity_unit" in i.message.lower() for i in pass3.issues),
                    billing_period_reasonable=not any("billing period" in i.message.lower() for i in pass3.issues if i.severity == "warning"),
                    negative_amounts_on_credits_only=not any("negative" in i.message.lower() for i in pass3.issues),
                    demand_present_if_expected=not any("demand" in i.message.lower() and "missing" in i.message.lower() for i in pass3.issues),
                    notes=[],
                ),
                audit_results=AuditResults(
                    fields_checked=pass4.fields_checked if pass4 else 0,
                    fields_matched=pass4.fields_matched if pass4 else 0,
                    fields_mismatched=len(pass4.mismatches) if pass4 else 0,
                    mismatches=[],
                    audit_model=pass4.audit_model if pass4 else "",
                ) if pass4 else None,
                overall_math_disposition=pass3.math_disposition,
            )

        return ExtractionResult(
            extraction_metadata=metadata,
            classification=cls,
            invoice=invoice,
            account=account,
            meters=[],  # Would be populated from merged_data
            charges=[],  # Would be populated from merged_data
            totals=Totals(),
            validation=validation,
            traceability=[],
            bounded_variance_record=BoundedVarianceRecord(is_reprocessing=False, drift_detected=False, drift_fields=[]),
        )
