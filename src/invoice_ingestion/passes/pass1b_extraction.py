"""Pass 1B: Vision Extraction -- Charges & Financial (Sonnet)."""
from __future__ import annotations
import json
import structlog
from ..llm.base import LLMClient
from ..llm.response_parser import extract_json_from_response
from ..models.internal import IngestionResult, ClassificationResult, Pass1AResult, Pass1BResult
from ..prompts.registry import PromptRegistry

logger = structlog.get_logger(__name__)


async def run_pass1b(
    ingestion: IngestionResult,
    classification: ClassificationResult,
    pass1a_result: Pass1AResult,
    llm_client: LLMClient,
    prompt_registry: PromptRegistry,
    few_shot_context: str | None = None,
) -> Pass1BResult:
    """Extract charges and financial data from all pages.

    Pass 1A output is injected as context so the model knows the invoice
    structure (account, meters) already extracted. This avoids duplication
    and gives the model anchoring data.
    """
    # Build images list (all pages)
    images = [p.image_base64 for p in ingestion.pages]

    # Determine which domain knowledge to inject (charge-specific)
    domain_files = ["cross_commodity"]
    if classification.commodity_type == "natural_gas":
        domain_files.append("gas_concepts")
    elif classification.commodity_type == "electricity":
        domain_files.append("electricity_concepts")
    elif classification.commodity_type == "water":
        domain_files.append("water_concepts")

    # Serialize Pass 1A output for context injection
    pass_1a_output = json.dumps({
        "invoice": pass1a_result.invoice,
        "account": pass1a_result.account,
        "meters": pass1a_result.meters,
    }, indent=2, default=str)

    # Build variables
    variables = {
        "commodity_type": classification.commodity_type,
        "country_code": classification.country_code or "US",
        "number_format": classification.number_format or "1,234.56",
        "date_format": classification.date_format or "MM/DD/YYYY",
        "language": classification.language,
        "pass_1a_output": pass_1a_output,
    }

    prompt = prompt_registry.render(
        "extraction_1b",
        variables=variables,
        few_shot_context=few_shot_context,
        domain_knowledge=domain_files,
    )

    response = await llm_client.complete_vision(
        system_prompt="You are an expert energy utility invoice analyst. Focus ONLY on charges, totals, VAT, and financial data. The invoice structure has already been extracted in a previous pass.",
        user_prompt=prompt,
        images=images,
        temperature=0.0,
        max_tokens=8192,
    )

    data = extract_json_from_response(response.content)

    return Pass1BResult(
        charges=data.get("charges", []),
        totals=data.get("totals", {}),
    )
