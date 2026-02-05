"""Pass 1A: Vision Extraction -- Structure & Metering (Sonnet)."""
from __future__ import annotations
import structlog
from ..llm.base import LLMClient
from ..llm.response_parser import extract_json_from_response
from ..models.internal import IngestionResult, ClassificationResult, Pass1AResult
from ..prompts.registry import PromptRegistry

logger = structlog.get_logger(__name__)


async def run_pass1a(
    ingestion: IngestionResult,
    classification: ClassificationResult,
    llm_client: LLMClient,
    prompt_registry: PromptRegistry,
    few_shot_context: str | None = None,
) -> Pass1AResult:
    """Extract invoice structure and metering data from all pages."""
    # Build images list (all pages)
    images = [p.image_base64 for p in ingestion.pages]

    # Determine which domain knowledge to inject
    domain_files = ["cross_commodity"]
    if classification.commodity_type == "natural_gas":
        domain_files.append("gas_concepts")
    elif classification.commodity_type == "electricity":
        domain_files.append("electricity_concepts")
    elif classification.commodity_type == "water":
        domain_files.append("water_concepts")

    # Build variables
    variables = {
        "commodity_type": classification.commodity_type,
        "country_code": classification.country_code or "US",
        "number_format": classification.number_format or "1,234.56",
        "date_format": classification.date_format or "MM/DD/YYYY",
        "language": classification.language,
    }

    prompt = prompt_registry.render(
        "extraction_1a",
        variables=variables,
        few_shot_context=few_shot_context,
        domain_knowledge=domain_files,
    )

    response = await llm_client.complete_vision(
        system_prompt="You are an expert energy utility invoice analyst. Focus ONLY on structural and metering data.",
        user_prompt=prompt,
        images=images,
        temperature=0.0,
        max_tokens=8192,
    )

    data = extract_json_from_response(response.content)

    return Pass1AResult(
        invoice=data.get("invoice", {}),
        account=data.get("account", {}),
        meters=data.get("meters", []),
    )
