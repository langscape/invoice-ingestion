"""Shared test fixtures."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from invoice_ingestion.llm.base import LLMClient, LLMResponse
from invoice_ingestion.config import Settings
from invoice_ingestion.prompts.registry import PromptRegistry
from invoice_ingestion.learning.correction_store import CorrectionStore


@pytest.fixture
def mock_settings():
    """Create test settings with dummy values."""
    return Settings(
        azure_ai_endpoint="https://test.eastus2.models.ai.azure.com",
        azure_ai_api_key="test-azure-ai-key",
        azure_openai_endpoint="https://test.openai.azure.com",
        azure_openai_api_key="test-azure-openai-key",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        blob_connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net",
    )


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock(spec=LLMClient)
    client.get_model_name.return_value = "mock-model"
    client.complete_text.return_value = LLMResponse(
        content='{"test": "response"}',
        model="mock-model",
        input_tokens=100,
        output_tokens=50,
    )
    client.complete_vision.return_value = LLMResponse(
        content='{"test": "response"}',
        model="mock-model",
        input_tokens=200,
        output_tokens=100,
    )
    return client


@pytest.fixture
def prompt_registry():
    return PromptRegistry()


@pytest.fixture
def correction_store():
    return CorrectionStore()
