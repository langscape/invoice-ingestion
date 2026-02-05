"""Pass 0.5: Classification & Routing -- Haiku vision."""
from __future__ import annotations
import structlog
from ..llm.base import LLMClient
from ..llm.response_parser import extract_json_from_response
from ..models.internal import IngestionResult, ClassificationResult
from ..models.classification import classify_complexity
from ..prompts.registry import PromptRegistry

logger = structlog.get_logger(__name__)


async def run_pass05(
    ingestion: IngestionResult,
    llm_client: LLMClient,
    prompt_registry: PromptRegistry,
    few_shot_context: str | None = None,
) -> ClassificationResult:
    """Classify the invoice using page 1 + one detail page."""
    # Select images: page 1 always, plus a middle page if multi-page
    images = [ingestion.pages[0].image_base64]
    if len(ingestion.pages) > 2:
        mid = len(ingestion.pages) // 2
        images.append(ingestion.pages[mid].image_base64)

    # Render prompt
    prompt = prompt_registry.render("classification", few_shot_context=few_shot_context)

    # Call LLM
    response = await llm_client.complete_vision(
        system_prompt="You are an expert energy utility invoice analyst.",
        user_prompt=prompt,
        images=images,
        temperature=0.0,
        max_tokens=2048,
    )

    # Parse response
    data = extract_json_from_response(response.content)

    # Derive complexity tier from signals
    signals = data.get("complexity_signals", [])
    complexity = classify_complexity(
        signals=signals,
        line_item_count=data.get("estimated_line_item_count", 0),
        page_count=len(ingestion.pages),
        has_multiple_vat_rates=data.get("has_multiple_vat_rates", False),
        has_calorific_conversion=data.get("has_calorific_conversion", False),
        has_contracted_capacity=data.get("has_contracted_capacity", False),
    )

    return ClassificationResult(
        commodity_type=data.get("commodity_type", "electricity"),
        commodity_confidence=data.get("commodity_confidence", 0.5),
        complexity_tier=complexity,
        complexity_signals=signals,
        market_type=data.get("market_type", "unknown"),
        has_supplier_split="supplier_split" in signals,
        has_demand_charges="demand_charges" in signals,
        has_tou="tou_present" in signals,
        has_net_metering="net_metering" in signals,
        has_prior_period_adjustments="prior_period_adjustments" in signals,
        estimated_line_item_count=data.get("estimated_line_item_count", 0),
        format_fingerprint=data.get("format_fingerprint", "unknown"),
        language=data.get("language", ingestion.language_detected),
        has_multiple_vat_rates=data.get("has_multiple_vat_rates", False),
        has_calorific_conversion=data.get("has_calorific_conversion", False),
        has_contracted_capacity=data.get("has_contracted_capacity", False),
        country_code=data.get("country_code"),
        number_format=data.get("number_format"),
        date_format=data.get("date_format"),
    )
