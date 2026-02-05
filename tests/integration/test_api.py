"""Integration tests for FastAPI endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from invoice_ingestion.api.app import create_app
from invoice_ingestion.config import Settings


@pytest.fixture
def client():
    settings = Settings(
        azure_ai_endpoint="https://test.eastus2.models.ai.azure.com",
        azure_ai_api_key="test-azure-ai-key",
        azure_openai_endpoint="https://test.openai.azure.com",
        azure_openai_api_key="test-azure-openai-key",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        blob_connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net",
    )
    app = create_app(settings)
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.integration
class TestHealthEndpoint:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.integration
class TestWebhookEndpoint:
    def test_blob_trigger(self, client):
        response = client.post("/webhook/blob-trigger", json={
            "blob_name": "test.pdf",
            "container": "imported",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
