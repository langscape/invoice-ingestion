"""Extract JSON from LLM responses."""
from __future__ import annotations
import json
import re


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response text.

    Strategies in order:
    1. Direct JSON parse of entire text
    2. Find ```json ... ``` block
    3. Find first { to last }
    """
    text = text.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: ```json block
    json_block = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', text, re.DOTALL)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: first { to last }
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response: {text[:200]}...")
