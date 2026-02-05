"""Test JSON extraction from LLM responses."""
import pytest
from invoice_ingestion.llm.response_parser import extract_json_from_response


class TestExtractJSON:
    def test_direct_json(self):
        result = extract_json_from_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_block(self):
        text = 'Here is the result:\n```json\n{"key": "value"}\n```\nDone.'
        result = extract_json_from_response(text)
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        text = 'The extraction is:\n{"key": "value"}\nAs shown above.'
        result = extract_json_from_response(text)
        assert result == {"key": "value"}

    def test_nested_json(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = extract_json_from_response(text)
        assert result["outer"]["inner"] == [1, 2, 3]

    def test_malformed_raises(self):
        with pytest.raises(ValueError):
            extract_json_from_response("This is not JSON at all")

    def test_whitespace_handling(self):
        result = extract_json_from_response('  \n  {"key": "value"}  \n  ')
        assert result == {"key": "value"}
