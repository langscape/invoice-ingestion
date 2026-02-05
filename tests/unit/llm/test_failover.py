"""Test failover LLM client."""
import pytest
from unittest.mock import AsyncMock
from invoice_ingestion.llm.base import LLMClient, LLMResponse
from invoice_ingestion.llm.failover import FailoverLLMClient


@pytest.fixture
def primary():
    client = AsyncMock(spec=LLMClient)
    client.get_model_name.return_value = "primary-model"
    return client

@pytest.fixture
def fallback():
    client = AsyncMock(spec=LLMClient)
    client.get_model_name.return_value = "fallback-model"
    return client


class TestFailover:
    @pytest.mark.asyncio
    async def test_primary_succeeds(self, primary, fallback):
        response = LLMResponse(content="ok", model="primary-model")
        primary.complete_text.return_value = response

        client = FailoverLLMClient(primary, fallback)
        result = await client.complete_text("sys", "user")

        assert result.content == "ok"
        primary.complete_text.assert_called_once()
        fallback.complete_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_primary_fails_fallback_called(self, primary, fallback):
        primary.complete_text.side_effect = Exception("rate limit")
        fallback_response = LLMResponse(content="fallback ok", model="fallback-model")
        fallback.complete_text.return_value = fallback_response

        client = FailoverLLMClient(primary, fallback)
        result = await client.complete_text("sys", "user")

        assert result.content == "fallback ok"
        assert client.failover_count == 1

    @pytest.mark.asyncio
    async def test_both_fail_raises(self, primary, fallback):
        primary.complete_text.side_effect = Exception("primary down")
        fallback.complete_text.side_effect = Exception("fallback down")

        client = FailoverLLMClient(primary, fallback)
        with pytest.raises(Exception):
            await client.complete_text("sys", "user")

    @pytest.mark.asyncio
    async def test_vision_failover(self, primary, fallback):
        primary.complete_vision.side_effect = Exception("timeout")
        fallback_response = LLMResponse(content="vision ok", model="fallback-model")
        fallback.complete_vision.return_value = fallback_response

        client = FailoverLLMClient(primary, fallback)
        result = await client.complete_vision("sys", "user", ["img"])

        assert result.content == "vision ok"
        assert client.failover_count == 1
