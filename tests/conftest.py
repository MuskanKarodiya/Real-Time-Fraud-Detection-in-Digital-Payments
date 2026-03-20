"""
Pytest Configuration and Shared Fixtures

This file is automatically discovered by pytest.
Fixtures defined here are available to all tests.
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, Mock
import numpy as np

from app.main import app
from app.model import model_service
from app.schemas import PredictionRequest, BatchPredictionRequest


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_features():
    """
    Valid 31-feature array for testing.

    Matches the expected input: V1-V28 (28 values) + amount_scaled + hour_sin + hour_cos
    """
    return [
        -1.36, 0.21, 1.48, -0.52, 1.23, -0.36, 0.45, -0.12,
        0.89, -0.78, 1.12, -0.34, 0.67, -1.45, 0.23, -0.89,
        1.34, -0.56, 0.78, -1.23, 0.45, -0.67, 1.89, -0.34,
        0.56, -0.78, 1.23, -0.45, 0.12, 0.89, -0.23
    ]


@pytest.fixture
def sample_transaction_request(sample_features):
    """Valid PredictionRequest for testing."""
    return PredictionRequest(
        transaction_id="test_txn_123",
        amount=150.50,
        features=sample_features
    )


@pytest.fixture
def sample_batch_requests(sample_features):
    """List of valid PredictionRequest objects for batch testing."""
    return [
        PredictionRequest(
            transaction_id=f"test_txn_{i}",
            amount=100.0 + i * 50,
            features=sample_features
        )
        for i in range(3)
    ]


@pytest.fixture
def valid_api_key():
    """Valid API key for testing."""
    return "dev-key-12345"


@pytest.fixture
def invalid_api_key():
    """Invalid API key for testing."""
    return "invalid-key-99999"


# ============================================================================
# Test Client Fixtures
# ============================================================================

@pytest.fixture
def client():
    """
    FastAPI TestClient for integration testing.

    Provides HTTP interface to the API without running a server.
    Automatically handles async operations.
    """
    return TestClient(app)


@pytest.fixture
def authenticated_client(client, valid_api_key):
    """
    TestClient with authentication pre-configured.

    Usage:
        def test_something(authenticated_client):
            response = authenticated_client.get("/api/v1/predict")
            # Request will have X-API-Key header
    """
    # Return a wrapper that adds the API key to every request
    class AuthenticatedClient:
        def __init__(self, test_client, api_key):
            self.client = test_client
            self.api_key = api_key

        def get(self, url, **kwargs):
            headers = kwargs.pop('headers', {})
            headers['X-API-Key'] = self.api_key
            return self.client.get(url, headers=headers, **kwargs)

        def post(self, url, **kwargs):
            headers = kwargs.pop('headers', {})
            headers['X-API-Key'] = self.api_key
            return self.client.post(url, headers=headers, **kwargs)

        def __getattr__(self, name):
            # Proxy other methods to the client
            def method_wrapper(**kwargs):
                headers = kwargs.pop('headers', {})
                headers['X-API-Key'] = self.api_key
                return getattr(self.client, name)(headers=headers, **kwargs)
            return method_wrapper

    return AuthenticatedClient(client, valid_api_key)


# ============================================================================
# Mock Model Fixture
# ============================================================================

@pytest.fixture
def mock_model_service():
    """
    Mock ModelService for unit testing.

    Avoids loading the actual model file.
    Returns predictable test results.
    """
    mock = MagicMock(spec=model_service)

    # Mock health check
    mock.health_check.return_value = True

    # Mock predict method
    mock.predict.return_value = {
        "fraud_probability": 0.25,
        "prediction": 0,
        "risk_level": "LOW",
        "threshold_used": 0.5
    }

    # Mock predict_batch method
    def mock_predict_batch(features_list, threshold=None):
        return [
            {
                "fraud_probability": 0.25,
                "prediction": 0,
                "risk_level": "LOW",
                "threshold_used": threshold or 0.5
            }
            for _ in features_list
        ]

    mock.predict_batch.side_effect = mock_predict_batch

    # Mock get_model_info
    mock.get_model_info.return_value = {
        "model_name": "Test Model",
        "model_version": "1.0.0",
        "algorithm": "XGBoost",
        "training_date": "2026-03-19T00:00:00Z",
        "feature_count": 31,
        "threshold": 0.5,
        "performance": {"roc_auc": 0.98}
    }

    return mock


# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """
    Pytest configuration hook.

    Called once at the start of the test run.
    """
    # Custom markers
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (slower, uses real dependencies)"
    )
    config.addinivalue_line(
        "markers",
        "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers",
        "api: mark test as API endpoint test"
    )
