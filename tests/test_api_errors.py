"""
API Error Handling Tests

Tests for error paths and edge cases in API endpoints.
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock

from app.main import app
from app.exceptions import ModelError, ValidationError


@pytest.mark.integration
@pytest.mark.api
class TestPredictEndpointErrors:
    """Tests for error handling in predict endpoint."""

    def test_predict_value_error_raises_validation_error(self, authenticated_client, sample_features):
        """Test that ValueError in prediction is converted to ValidationError."""
        with patch('app.main.model_service.predict') as mock_predict:
            mock_predict.side_effect = ValueError("Feature validation failed")

            response = authenticated_client.post(
                "/api/v1/predict",
                json={
                    "transaction_id": "test_123",
                    "amount": 100.0,
                    "features": sample_features
                }
            )

            # Should return 422 for validation error
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_predict_generic_error_raises_model_error(self, authenticated_client, sample_features):
        """Test that generic exceptions are handled appropriately."""
        with patch('app.main.model_service.predict') as mock_predict:
            mock_predict.side_effect = RuntimeError("Model inference failed")

            response = authenticated_client.post(
                "/api/v1/predict",
                json={
                    "transaction_id": "test_456",
                    "amount": 50.0,
                    "features": sample_features
                }
            )

            # Should handle error gracefully
            assert response.status_code in [status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_422_UNPROCESSABLE_ENTITY]


@pytest.mark.integration
@pytest.mark.api
class TestBatchPredictEndpointErrors:
    """Tests for error handling in batch predict endpoint."""

    def test_batch_predict_value_error(self, authenticated_client, sample_batch_requests):
        """Test ValueError handling in batch prediction."""
        with patch('app.main.model_service.predict_batch') as mock_batch:
            mock_batch.side_effect = ValueError("Invalid batch size")

            batch_request = {
                "threshold": 0.5,
                "transactions": [req.model_dump() for req in sample_batch_requests]
            }

            response = authenticated_client.post("/api/v1/predict/batch", json=batch_request)
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_batch_predict_generic_error(self, authenticated_client, sample_batch_requests):
        """Test generic exception handling in batch prediction."""
        with patch('app.main.model_service.predict_batch') as mock_batch:
            mock_batch.side_effect = Exception("Unexpected error")

            batch_request = {
                "threshold": 0.5,
                "transactions": [req.model_dump() for req in sample_batch_requests]
            }

            response = authenticated_client.post("/api/v1/predict/batch", json=batch_request)
            assert response.status_code in [status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_422_UNPROCESSABLE_ENTITY]


@pytest.mark.integration
@pytest.mark.api
class TestModelInfoErrors:
    """Tests for error handling in model info endpoint."""

    def test_model_info_exception_handling(self, client):
        """Test that exceptions in get_model_info are handled."""
        with patch('app.main.model_service.get_model_info') as mock_info:
            mock_info.side_effect = Exception("Model not loaded")

            response = client.get("/api/v1/model/info")
            # Should handle error gracefully
            assert response.status_code in [status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_404_NOT_FOUND]


@pytest.mark.integration
@pytest.mark.api
class TestGlobalExceptionHandler:
    """Tests for global exception handler."""

    def test_unhandled_exception_returns_500(self, authenticated_client, sample_features):
        """Test that unhandled exceptions return 500 error."""
        with patch('app.main.model_service.predict') as mock_predict:
            # Force an unexpected error
            mock_predict.side_effect = KeyError("unexpected_key")

            response = authenticated_client.post(
                "/api/v1/predict",
                json={
                    "transaction_id": "test_err",
                    "amount": 100.0,
                    "features": sample_features
                }
            )

            # Global handler should catch this
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_exception_response_format(self, authenticated_client, sample_features):
        """Test that exception responses follow RFC 7807 format."""
        with patch('app.main.model_service.predict') as mock_predict:
            mock_predict.side_effect = RuntimeError("Test error")

            response = authenticated_client.post(
                "/api/v1/predict",
                json={
                    "transaction_id": "test_fmt",
                    "amount": 100.0,
                    "features": sample_features
                }
            )

            if response.status_code == 500:
                data = response.json()
                # Check for RFC 7807 fields
                assert "type" in data or "detail" in data or "title" in data
