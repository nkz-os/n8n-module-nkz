"""
n8n Integration Hub Backend - API Tests
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_health_requires_no_auth(self, client):
        """Health endpoint should work without auth."""
        response = client.get("/health")
        assert response.status_code == 200


class TestN8nEndpoints:
    """Test n8n workflow endpoints."""
    
    @patch('app.routers.n8n.n8n_request')
    def test_list_workflows_mock(self, mock_request, client):
        """Test listing workflows with mock."""
        mock_request.return_value = {
            "data": [
                {"id": "1", "name": "Test Workflow", "active": True}
            ]
        }
        
        # Note: Would need to mock auth for real test
        # This is a placeholder showing test structure
        pass
    
    def test_workflow_endpoints_require_auth(self, client):
        """Workflow endpoints should require authentication."""
        response = client.get("/api/n8n-nkz/n8n/workflows")
        assert response.status_code == 401


class TestSentinelEndpoints:
    """Test Sentinel/NDVI endpoints."""
    
    def test_sentinel_endpoints_require_auth(self, client):
        """Sentinel endpoints should require authentication."""
        response = client.get("/api/n8n-nkz/sentinel/alerts")
        assert response.status_code == 401


class TestIntelligenceEndpoints:
    """Test Intelligence AI endpoints."""
    
    def test_intelligence_endpoints_require_auth(self, client):
        """Intelligence endpoints should require authentication."""
        response = client.get("/api/n8n-nkz/intelligence/plugins")
        assert response.status_code == 401


class TestWebhookEndpoints:
    """Test webhook endpoints."""
    
    def test_inbound_webhook_no_auth(self, client):
        """Inbound webhook should work without auth (uses secret verification)."""
        response = client.post(
            "/api/n8n-nkz/webhooks/inbound",
            json={"event": "test", "data": {}}
        )
        assert response.status_code == 204
        assert response.content == b""

    def test_inbound_webhook_answers_204_without_body(self, client):
        """Orion-LD pauses a subscription after three replies it cannot read."""
        response = client.post(
            "/api/n8n-nkz/webhooks/inbound",
            json={"data": []},
            headers={"NGSILD-Tenant": "acme"},
        )
        assert response.status_code == 204
        assert response.content == b""

    def test_inbound_webhook_rejects_invalid_json(self, client):
        response = client.post(
            "/api/n8n-nkz/webhooks/inbound",
            content="{not json",
            headers={"Content-Type": "application/json", "NGSILD-Tenant": "acme"},
        )
        assert response.status_code == 400


class TestOpenAPI:
    """Test OpenAPI documentation."""
    
    def test_openapi_available(self, client):
        """OpenAPI spec should be available."""
        response = client.get("/api/n8n-nkz/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
    
    def test_docs_available(self, client):
        """Swagger docs should be available."""
        response = client.get("/api/n8n-nkz/docs")
        assert response.status_code == 200
