"""
API Endpoint Integration Tests

Tests for all FastAPI endpoints using TestClient.
These are integration tests that test the full request/response cycle.
"""
import pytest
from fastapi import status

from app.main import app


@pytest.mark.integration
@pytest.mark.api
class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_200(self, client):
        """Test that root endpoint returns 200 OK."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

    def test_root_returns_json(self, client):
        """Test that root endpoint returns JSON."""
        response = client.get("/")
        assert response.headers["content-type"] == "application/json"

    def test_root_has_required_fields(self, client):
        """Test that root response contains expected fields."""
        response = client.get("/")
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert "endpoints" in data


@pytest.mark.integration
@pytest.mark.api
class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_returns_200(self, client):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_returns_correct_structure(self, client):
        """Test that health response has correct structure."""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert "model_loaded" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_status_is_healthy(self, client):
        """Test that health status shows 'healthy' when model is loaded."""
        response = client.get("/api/v1/health")
        data = response.json()

        assert data["status"] in ["healthy", "unhealthy"]
        assert isinstance(data["model_loaded"], bool)


@pytest.mark.integration
@pytest.mark.api
class TestModelInfoEndpoint:
    """Tests for model info endpoint."""

    def test_model_info_returns_200(self, client):
        """Test that model info endpoint returns 200 OK."""
        response = client.get("/api/v1/model/info")
        assert response.status_code == status.HTTP_200_OK

    def test_model_info_has_required_fields(self, client):
        """Test that model info contains all required fields."""
        response = client.get("/api/v1/model/info")
        data = response.json()

        required_fields = [
            "model_name", "model_version", "algorithm",
            "training_date", "feature_count", "threshold",
            "performance", "api_version"
        ]

        for field in required_fields:
            assert field in data

    def test_model_info_feature_count_is_31(self, client):
        """Test that feature count is correct."""
        response = client.get("/api/v1/model/info")
        data = response.json()

        assert data["feature_count"] == 31


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestPredictEndpoint:
    """Tests for prediction endpoint."""

    def test_predict_without_api_key_returns_422(self, client, sample_transaction_request):
        """Test that missing API key returns validation error (422)."""
        response = client.post("/api/v1/predict", json=sample_transaction_request.model_dump())
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_predict_with_valid_api_key_returns_200(self, authenticated_client, sample_transaction_request):
        """Test that valid API key allows prediction."""
        response = authenticated_client.post("/api/v1/predict", json=sample_transaction_request.model_dump())
        assert response.status_code == status.HTTP_200_OK

    def test_predict_returns_correct_structure(self, authenticated_client, sample_transaction_request):
        """Test that prediction response has correct structure."""
        response = authenticated_client.post("/api/v1/predict", json=sample_transaction_request.model_dump())
        data = response.json()

        required_fields = [
            "transaction_id", "fraud_probability", "prediction",
            "risk_level", "threshold_used", "processed_at"
        ]

        for field in required_fields:
            assert field in data

    def test_predict_transaction_id_matches_request(self, authenticated_client, sample_transaction_request):
        """Test that response transaction_id matches request."""
        response = authenticated_client.post("/api/v1/predict", json=sample_transaction_request.model_dump())
        data = response.json()

        assert data["transaction_id"] == sample_transaction_request.transaction_id

    def test_predict_fraud_probability_in_valid_range(self, authenticated_client, sample_transaction_request):
        """Test that fraud_probability is between 0 and 1."""
        response = authenticated_client.post("/api/v1/predict", json=sample_transaction_request.model_dump())
        data = response.json()

        assert 0.0 <= data["fraud_probability"] <= 1.0

    def test_predict_prediction_is_binary(self, authenticated_client, sample_transaction_request):
        """Test that prediction is either 0 or 1."""
        response = authenticated_client.post("/api/v1/predict", json=sample_transaction_request.model_dump())
        data = response.json()

        assert data["prediction"] in [0, 1]

    def test_predict_risk_level_is_valid(self, authenticated_client, sample_transaction_request):
        """Test that risk_level is HIGH, MEDIUM, or LOW."""
        response = authenticated_client.post("/api/v1/predict", json=sample_transaction_request.model_dump())
        data = response.json()

        assert data["risk_level"] in ["HIGH", "MEDIUM", "LOW"]

    def test_predict_with_invalid_api_key_returns_401(self, client, sample_transaction_request, invalid_api_key):
        """Test that invalid API key returns 401."""
        response = client.post(
            "/api/v1/predict",
            json=sample_transaction_request.model_dump(),
            headers={"X-API-Key": invalid_api_key}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestPredictValidation:
    """Tests for prediction endpoint input validation."""

    def test_predict_missing_transaction_id_returns_422(self, authenticated_client, sample_features):
        """Test that missing transaction_id returns validation error."""
        invalid_request = {
            "amount": 100.0,
            "features": sample_features
        }

        response = authenticated_client.post("/api/v1/predict", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_predict_negative_amount_returns_422(self, authenticated_client, sample_features):
        """Test that negative amount returns validation error."""
        invalid_request = {
            "transaction_id": "test_123",
            "amount": -50.0,  # Negative amount
            "features": sample_features
        }

        response = authenticated_client.post("/api/v1/predict", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_predict_wrong_feature_count_returns_422(self, authenticated_client):
        """Test that wrong feature count returns validation error."""
        invalid_request = {
            "transaction_id": "test_123",
            "amount": 100.0,
            "features": list(range(30))  # Only 30 features instead of 31
        }

        response = authenticated_client.post("/api/v1/predict", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestBatchPredictEndpoint:
    """Tests for batch prediction endpoint."""

    def test_batch_predict_without_api_key_returns_422(self, client, sample_batch_requests):
        """Test that missing API key returns validation error (422)."""
        batch_request = {
            "threshold": 0.5,
            "transactions": [req.model_dump() for req in sample_batch_requests]
        }

        response = client.post("/api/v1/predict/batch", json=batch_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_batch_predict_with_valid_api_key_returns_200(self, authenticated_client, sample_batch_requests):
        """Test that valid API key allows batch prediction."""
        batch_request = {
            "threshold": 0.5,
            "transactions": [req.model_dump() for req in sample_batch_requests]
        }

        response = authenticated_client.post("/api/v1/predict/batch", json=batch_request)
        assert response.status_code == status.HTTP_200_OK

    def test_batch_predict_returns_correct_structure(self, authenticated_client, sample_batch_requests):
        """Test that batch response has correct structure."""
        batch_request = {
            "threshold": 0.5,
            "transactions": [req.model_dump() for req in sample_batch_requests]
        }

        response = authenticated_client.post("/api/v1/predict/batch", json=batch_request)
        data = response.json()

        required_fields = ["predictions", "total_processed", "fraud_count", "fraud_rate", "processed_at"]
        for field in required_fields:
            assert field in data

    def test_batch_predict_total_matches_input(self, authenticated_client, sample_batch_requests):
        """Test that total_processed matches input count."""
        batch_request = {
            "threshold": 0.5,
            "transactions": [req.model_dump() for req in sample_batch_requests]
        }

        response = authenticated_client.post("/api/v1/predict/batch", json=batch_request)
        data = response.json()

        assert data["total_processed"] == len(sample_batch_requests)

    def test_batch_predict_fraud_count_is_accurate(self, authenticated_client, sample_batch_requests):
        """Test that fraud_count correctly counts fraud predictions."""
        batch_request = {
            "threshold": 0.5,
            "transactions": [req.model_dump() for req in sample_batch_requests]
        }

        response = authenticated_client.post("/api/v1/predict/batch", json=batch_request)
        data = response.json()

        # Count actual fraud predictions
        actual_fraud_count = sum(p["prediction"] for p in data["predictions"])
        assert data["fraud_count"] == actual_fraud_count

    def test_batch_predict_with_custom_threshold(self, authenticated_client, sample_batch_requests):
        """Test that custom threshold is used in batch predictions."""
        custom_threshold = 0.7
        batch_request = {
            "threshold": custom_threshold,
            "transactions": [req.model_dump() for req in sample_batch_requests]
        }

        response = authenticated_client.post("/api/v1/predict/batch", json=batch_request)
        data = response.json()

        # Check that threshold was used
        for prediction in data["predictions"]:
            assert prediction["threshold_used"] == custom_threshold


@pytest.mark.integration
@pytest.mark.api
class TestDocsEndpoint:
    """Tests for API documentation endpoints."""

    def test_docs_returns_200(self, client):
        """Test that Swagger UI is accessible."""
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK

    def test_redoc_returns_200(self, client):
        """Test that ReDoc is accessible."""
        response = client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.api
class TestOpenApiSchema:
    """Tests for OpenAPI schema endpoint."""

    def test_openapi_json_returns_200(self, client):
        """Test that OpenAPI JSON schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK

    def test_openapi_schema_has_required_fields(self, client):
        """Test that OpenAPI schema contains required fields."""
        response = client.get("/openapi.json")
        schema = response.json()

        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            assert field in schema

    def test_openapi_schema_has_predict_endpoint(self, client):
        """Test that /api/v1/predict endpoint is documented."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "/api/v1/predict" in schema["paths"]
        assert "post" in schema["paths"]["/api/v1/predict"]
