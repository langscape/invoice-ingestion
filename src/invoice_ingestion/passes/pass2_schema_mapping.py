"""Pass 2: Schema Mapping & Normalisation -- Haiku text-only."""
from __future__ import annotations
import json
import structlog
from ..llm.base import LLMClient
from ..llm.response_parser import extract_json_from_response
from ..models.internal import ClassificationResult, Pass1AResult, Pass1BResult, Pass2Result
from ..prompts.registry import PromptRegistry

logger = structlog.get_logger(__name__)


async def run_pass2(
    classification: ClassificationResult,
    pass1a_result: Pass1AResult,
    pass1b_result: Pass1BResult,
    llm_client: LLMClient,
    prompt_registry: PromptRegistry,
) -> Pass2Result:
    """Merge and normalize extracted data into the final schema.

    Takes raw extraction outputs from Pass 1A (structure/metering) and
    Pass 1B (charges/financial) and sends the merged JSON to Haiku for:
    - Unit normalization (e.g. kWh, therms, ccf)
    - Charge classification (category, section, owner)
    - Temporal attribution (current period vs. prior period adjustments)
    - Field naming normalization to match output schema
    """
    # Merge Pass 1A and Pass 1B into a single JSON payload
    merged_extraction = {
        "invoice": pass1a_result.invoice,
        "account": pass1a_result.account,
        "meters": pass1a_result.meters,
        "charges": pass1b_result.charges,
        "totals": pass1b_result.totals,
        "classification": {
            "commodity_type": classification.commodity_type,
            "complexity_tier": classification.complexity_tier,
            "market_type": classification.market_type,
            "country_code": classification.country_code,
            "number_format": classification.number_format,
            "date_format": classification.date_format,
            "language": classification.language,
            "has_supplier_split": classification.has_supplier_split,
            "has_demand_charges": classification.has_demand_charges,
            "has_tou": classification.has_tou,
            "has_net_metering": classification.has_net_metering,
            "has_multiple_vat_rates": classification.has_multiple_vat_rates,
            "has_calorific_conversion": classification.has_calorific_conversion,
            "has_contracted_capacity": classification.has_contracted_capacity,
        },
    }

    # Serialize Pass 1A and 1B outputs separately for the prompt
    pass_1a_json = json.dumps({
        "invoice": pass1a_result.invoice,
        "account": pass1a_result.account,
        "meters": pass1a_result.meters,
    }, indent=2, default=str)

    pass_1b_json = json.dumps({
        "charges": pass1b_result.charges if pass1b_result else [],
        "totals": pass1b_result.totals if pass1b_result else {},
    }, indent=2, default=str)

    logger.info("pass2_input_data",
                invoice_number=pass1a_result.invoice.get("invoice_number", {}).get("value") if isinstance(pass1a_result.invoice.get("invoice_number"), dict) else pass1a_result.invoice.get("invoice_number"),
                customer_name=pass1a_result.account.get("customer_name", {}).get("value") if isinstance(pass1a_result.account.get("customer_name"), dict) else pass1a_result.account.get("customer_name"))

    # Build variables for prompt template (must match placeholders in schema_mapping.md)
    variables = {
        "pass_1a_output": pass_1a_json,
        "pass_1b_output": pass_1b_json,
        "commodity_type": classification.commodity_type,
        "market_type": classification.market_type or "regulated",
        "country_code": classification.country_code or "US",
        "language": classification.language or "en",
        "number_format": classification.number_format or "1,234.56",
        "date_format": classification.date_format or "MM/DD/YYYY",
    }

    prompt = prompt_registry.render("schema_mapping", variables=variables)

    response = await llm_client.complete_text(
        system_prompt=(
            "You are a data normalization specialist for energy utility invoices. "
            "Your task is to normalize, classify, and map extracted invoice data into "
            "a standardized output schema. Ensure all units are normalized, charges are "
            "properly classified, and temporal attribution is correct. "
            "Respond with valid JSON only."
        ),
        user_prompt=prompt,
        temperature=0.0,
        max_tokens=8192,
        json_mode=True,
    )

    data = extract_json_from_response(response.content)

    # Safely extract values for logging
    inv_num = data.get("invoice", {}).get("invoice_number")
    inv_num_val = inv_num.get("value") if isinstance(inv_num, dict) else inv_num
    cust_name = data.get("account", {}).get("customer_name")
    cust_name_val = cust_name.get("value") if isinstance(cust_name, dict) else cust_name

    logger.info("pass2_output_data",
                invoice_number=inv_num_val,
                customer_name=cust_name_val,
                response_preview=response.content[:500])

    logger.info(
        "pass2_schema_mapping_complete",
        charge_count=len(data.get("charges", [])),
        meter_count=len(data.get("meters", [])),
    )

    return Pass2Result(data=data)
