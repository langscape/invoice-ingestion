"""Pipeline orchestrator: Pass 0 → 0.5 → 1A → 1B → 2 → 3 → 4 → confidence gate."""
from __future__ import annotations
import json
import time
import structlog
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import Settings
from .storage.database import get_engine, AsyncSessionLocal
from .storage.models import Extraction
from .storage.repositories import ExtractionRepo
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
    MonetaryAmount, ConfidentValue, MathDisposition, BillingPeriod,
    ChargeCategory, ChargeOwner, ChargeSection, MathCheck, ChargePeriod,
    AttributionType, Consumption, ReadType, Demand, DemandType, TOUPeriod,
    VATSummaryEntry, VATCategory,
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
        """Initialize LLM clients — all models deployed via Azure.

        If azure_ai_endpoint is configured, uses Claude for classification/extraction/mapping
        and GPT-4o for audit. Otherwise, uses GPT-4o (Azure OpenAI) for all passes.
        """
        azure_ai_key = self.settings.azure_ai_api_key.get_secret_value()
        azure_ai_endpoint = self.settings.azure_ai_endpoint
        azure_openai_key = self.settings.azure_openai_api_key.get_secret_value()
        azure_openai_endpoint = self.settings.azure_openai_endpoint

        if azure_ai_endpoint and azure_ai_key:
            # Claude models via Azure AI Foundry
            logger.info("llm_init", mode="azure_ai_claude", extraction_model=self.settings.extraction_model)

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
        else:
            # All passes use GPT-4o via Azure OpenAI
            logger.info("llm_init", mode="azure_openai_only", extraction_model=self.settings.extraction_model)

            self._classification_client: LLMClient = OpenAIClient(
                api_key=azure_openai_key,
                model=self.settings.classification_model,
                azure_endpoint=azure_openai_endpoint,
            )

            self._extraction_client: LLMClient = OpenAIClient(
                api_key=azure_openai_key,
                model=self.settings.extraction_model,
                azure_endpoint=azure_openai_endpoint,
            )

            self._schema_mapping_client: LLMClient = OpenAIClient(
                api_key=azure_openai_key,
                model=self.settings.schema_mapping_model,
                azure_endpoint=azure_openai_endpoint,
            )

        # Audit: always GPT-4o via Azure OpenAI
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

        # Load corrections from database for learning loop
        if self.settings.enable_learning_loop:
            await self.correction_store.load_from_database()

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

        # --- Store result in database ---
        await self._store_result(result, blob_name, file_bytes)

        logger.info("pipeline_complete", extraction_id=str(extraction_id),
                    confidence=confidence_score, tier=confidence_tier,
                    processing_time_ms=processing_time)

        return result

    async def _store_result(
        self,
        result: ExtractionResult,
        blob_name: str,
        file_bytes: bytes,
    ) -> None:
        """Store extraction result in database and PDF in local storage."""
        extraction_id = result.extraction_metadata.extraction_id

        # Determine status based on confidence tier
        tier = result.extraction_metadata.confidence_tier.value
        if tier == "auto_accept":
            status = "accepted"
        else:
            status = "pending_review"

        # Create Extraction model
        extraction = Extraction(
            extraction_id=extraction_id,
            file_hash=result.extraction_metadata.source_document.file_hash,
            blob_name=blob_name,
            status=status,
            result_json=result.model_dump(mode="json"),
            confidence_score=result.extraction_metadata.overall_confidence,
            confidence_tier=tier,
            commodity_type=result.classification.commodity_type.value,
            utility_provider=result.account.utility_provider.value if result.account.utility_provider else "Unknown",
            processing_time_ms=result.extraction_metadata.processing_time_ms,
        )

        # Store in database
        async with AsyncSessionLocal() as session:
            repo = ExtractionRepo(session)
            await repo.create(extraction)
            await session.commit()

        # Store PDF in local storage for development
        local_storage = Path(self.settings.local_storage_path)
        pdf_dir = local_storage / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f"{extraction_id}.pdf"
        pdf_path.write_bytes(file_bytes)

        logger.info("result_stored", extraction_id=str(extraction_id), status=status, pdf_path=str(pdf_path))

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
        # Helper to safely extract ConfidentValue from mixed formats
        def _cv(data: dict | str | None, default: str = "") -> ConfidentValue:
            """Extract ConfidentValue from dict or plain value."""
            if data is None:
                return ConfidentValue(value=default, confidence=0.0)
            if isinstance(data, dict):
                return ConfidentValue(
                    value=data.get("value", default),
                    confidence=data.get("confidence", 0.9),
                    source_location=data.get("source_location"),
                )
            # Plain value (string, number, etc.)
            return ConfidentValue(value=data, confidence=0.9)

        def _cv_date(data: dict | str | None) -> ConfidentValue:
            """Extract ConfidentValue[date] from dict or plain value, parsing date strings."""
            from datetime import date as date_type
            if data is None:
                return ConfidentValue(value=None, confidence=0.0)
            if isinstance(data, dict):
                raw_val = data.get("value")
                conf = data.get("confidence", 0.9)
                src = data.get("source_location")
            else:
                raw_val = data
                conf = 0.9
                src = None

            # Parse date string
            if raw_val is None or raw_val == "":
                return ConfidentValue(value=None, confidence=0.0, source_location=src)
            if isinstance(raw_val, date_type):
                return ConfidentValue(value=raw_val, confidence=conf, source_location=src)
            # Try parsing common date formats
            if isinstance(raw_val, str):
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y"):
                    try:
                        parsed = datetime.strptime(raw_val, fmt).date()
                        return ConfidentValue(value=parsed, confidence=conf, source_location=src)
                    except ValueError:
                        continue
            # Could not parse
            return ConfidentValue(value=None, confidence=0.0, source_location=src)

        invoice_data = merged_data.get("invoice", {})

        # Build billing_period if present
        billing_period = None
        bp_data = invoice_data.get("billing_period")
        if bp_data and isinstance(bp_data, dict):
            bp_start = _cv_date(bp_data.get("start"))
            bp_end = _cv_date(bp_data.get("end"))
            bp_days = bp_data.get("days", 0)
            if bp_start.value and bp_end.value:
                billing_period = BillingPeriod(start=bp_start, end=bp_end, days=bp_days)

        invoice = Invoice(
            invoice_number=_cv(invoice_data.get("invoice_number")),
            invoice_date=_cv_date(invoice_data.get("invoice_date")),
            due_date=_cv_date(invoice_data.get("due_date")),
            billing_period=billing_period,
            rate_schedule=_cv(invoice_data.get("rate_schedule")) if invoice_data.get("rate_schedule") else None,
            statement_type=invoice_data.get("statement_type", "regular"),
        )

        account_data = merged_data.get("account", {})
        account = Account(
            account_number=_cv(account_data.get("account_number")),
            customer_name=_cv(account_data.get("customer_name")),
            service_address=_cv(account_data.get("service_address")),
            utility_provider=_cv(account_data.get("utility_provider")),
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

        # Build charges from merged_data
        charges = []
        for idx, c in enumerate(merged_data.get("charges", [])):
            try:
                # Build MonetaryAmount for amount
                amt_data = c.get("amount", {})
                amount = MonetaryAmount(
                    value=amt_data.get("value", 0.0),
                    currency=amt_data.get("currency", "USD"),
                    original_string=amt_data.get("original_string"),
                    confidence=amt_data.get("confidence", 0.9),
                    source_location=amt_data.get("source_location"),
                )

                # Build MathCheck if present
                math_check = None
                mc_data = c.get("math_check")
                if mc_data and isinstance(mc_data, dict):
                    math_check = MathCheck(
                        expected_amount=mc_data.get("expected_amount", 0.0),
                        calculation=mc_data.get("calculation", ""),
                        matches_stated=mc_data.get("matches_stated", True),
                        variance=mc_data.get("variance", 0.0),
                        utility_adjustment_detected=mc_data.get("utility_adjustment_detected", False),
                        adjustment_note=mc_data.get("adjustment_note"),
                    )

                # Build ChargePeriod if present
                charge_period = None
                cp_data = c.get("charge_period")
                if cp_data and isinstance(cp_data, dict):
                    cp_start = cp_data.get("start")
                    cp_end = cp_data.get("end")
                    if cp_start and cp_end:
                        charge_period = ChargePeriod(
                            start=datetime.strptime(cp_start, "%Y-%m-%d").date() if isinstance(cp_start, str) else cp_start,
                            end=datetime.strptime(cp_end, "%Y-%m-%d").date() if isinstance(cp_end, str) else cp_end,
                            attribution_type=AttributionType(cp_data.get("attribution_type", "current")),
                            reference_period_note=cp_data.get("reference_period_note"),
                        )

                charge = Charge(
                    line_id=c.get("line_id", f"L{idx+1:03d}"),
                    description=_cv(c.get("description")),
                    category=ChargeCategory(c.get("category", "other")),
                    subcategory=c.get("subcategory"),
                    charge_owner=ChargeOwner(c.get("charge_owner", "utility")),
                    charge_section=ChargeSection(c.get("charge_section", "other")),
                    quantity=_cv(c.get("quantity")) if c.get("quantity") else None,
                    rate=_cv(c.get("rate")) if c.get("rate") else None,
                    amount=amount,
                    charge_period=charge_period,
                    applies_to_meter=c.get("applies_to_meter"),
                    math_check=math_check,
                    vat_rate=c.get("vat_rate"),
                    vat_category=VATCategory(c.get("vat_category")) if c.get("vat_category") else None,
                )
                charges.append(charge)
            except Exception as e:
                logger.warning("charge_mapping_failed", index=idx, error=str(e))

        # Build meters from merged_data
        meters = []
        for idx, m in enumerate(merged_data.get("meters", [])):
            try:
                # Build Consumption
                cons_data = m.get("consumption", {})
                consumption = Consumption(
                    raw_value=cons_data.get("raw_value", 0.0),
                    raw_unit=cons_data.get("raw_unit", "kWh"),
                    normalized_value=cons_data.get("normalized_value"),
                    normalized_unit=cons_data.get("normalized_unit"),
                    normalization_formula=cons_data.get("normalization_formula"),
                )

                # Build Demand if present
                demand = None
                dem_data = m.get("demand")
                if dem_data and isinstance(dem_data, dict) and dem_data.get("value"):
                    demand = Demand(
                        value=dem_data.get("value", 0.0),
                        unit=dem_data.get("unit", "kW"),
                        demand_type=DemandType(dem_data.get("demand_type", "non_coincident")),
                        peak_datetime=dem_data.get("peak_datetime"),
                        source_location=dem_data.get("source_location"),
                    )

                # Build TOU breakdown if present
                tou_breakdown = None
                tou_data = m.get("tou_breakdown")
                if tou_data and isinstance(tou_data, list):
                    tou_breakdown = []
                    for tou in tou_data:
                        tou_breakdown.append(TOUPeriod(
                            period=tou.get("period", ""),
                            consumption=_cv(tou.get("consumption")),
                            demand=_cv(tou.get("demand")) if tou.get("demand") else None,
                        ))

                meter = Meter(
                    meter_number=_cv(m.get("meter_number")),
                    service_point_id=m.get("service_point_id"),
                    read_type=ReadType(m.get("read_type", "actual")),
                    read_date_start=datetime.strptime(m["read_date_start"], "%Y-%m-%d").date() if m.get("read_date_start") else None,
                    read_date_end=datetime.strptime(m["read_date_end"], "%Y-%m-%d").date() if m.get("read_date_end") else None,
                    previous_read=m.get("previous_read"),
                    current_read=m.get("current_read"),
                    multiplier=_cv(m.get("multiplier")) if m.get("multiplier") else None,
                    loss_factor=_cv(m.get("loss_factor")) if m.get("loss_factor") else None,
                    consumption=consumption,
                    demand=demand,
                    generation=m.get("generation"),
                    net_consumption=m.get("net_consumption"),
                    tou_breakdown=tou_breakdown,
                )
                meters.append(meter)
            except Exception as e:
                logger.warning("meter_mapping_failed", index=idx, error=str(e))

        # Build totals from merged_data
        def _monetary(data: dict | None) -> MonetaryAmount | None:
            if not data or not isinstance(data, dict):
                return None
            return MonetaryAmount(
                value=data.get("value", 0.0),
                currency=data.get("currency", "USD"),
                original_string=data.get("original_string"),
                confidence=data.get("confidence", 0.9),
                source_location=data.get("source_location"),
            )

        totals_data = merged_data.get("totals", {})

        # Build VAT summary if present
        vat_summary = None
        vat_data = totals_data.get("vat_summary")
        if vat_data and isinstance(vat_data, list):
            vat_summary = []
            for v in vat_data:
                try:
                    vat_summary.append(VATSummaryEntry(
                        vat_rate=v.get("vat_rate", 0.0),
                        vat_category=VATCategory(v.get("vat_category", "standard")),
                        taxable_base=_monetary(v.get("taxable_base")) or MonetaryAmount(value=0.0, currency="USD"),
                        vat_amount=_monetary(v.get("vat_amount")) or MonetaryAmount(value=0.0, currency="USD"),
                    ))
                except Exception as e:
                    logger.warning("vat_summary_mapping_failed", error=str(e))

        totals = Totals(
            supply_subtotal=_monetary(totals_data.get("supply_subtotal")),
            distribution_subtotal=_monetary(totals_data.get("distribution_subtotal")),
            taxes_subtotal=_monetary(totals_data.get("taxes_subtotal")),
            current_charges=_monetary(totals_data.get("current_charges")),
            previous_balance=_monetary(totals_data.get("previous_balance")),
            payments_received=_monetary(totals_data.get("payments_received")),
            late_fees=_monetary(totals_data.get("late_fees")),
            total_amount_due=_monetary(totals_data.get("total_amount_due")),
            budget_billing_amount=_monetary(totals_data.get("budget_billing_amount")),
            minimum_bill_applied=totals_data.get("minimum_bill_applied", False),
            vat_summary=vat_summary,
            total_net=_monetary(totals_data.get("total_net")),
            total_vat=_monetary(totals_data.get("total_vat")),
            total_gross=_monetary(totals_data.get("total_gross")),
            reverse_charge_applied=totals_data.get("reverse_charge_applied", False),
        )

        return ExtractionResult(
            extraction_metadata=metadata,
            classification=cls,
            invoice=invoice,
            account=account,
            meters=meters,
            charges=charges,
            totals=totals,
            validation=validation,
            traceability=[],
            bounded_variance_record=BoundedVarianceRecord(is_reprocessing=False, drift_detected=False, drift_fields=[]),
        )
