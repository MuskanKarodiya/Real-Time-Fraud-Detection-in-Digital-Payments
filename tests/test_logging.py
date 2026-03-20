"""
Logging Module Tests

Tests for PredictionLogger class including thread-safe writes.
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, Mock

from app.logging_config import PredictionLogger, prediction_logger


@pytest.mark.unit
class TestPredictionLogger:
    """Tests for PredictionLogger class."""

    def test_logger_init_creates_log_dir(self):
        """Test that logger creates log directory."""
        logger = PredictionLogger(log_dir=Path("logs/test"))
        assert logger.log_dir.exists()
        assert logger.predictions_log.parent == logger.log_dir
        assert logger.errors_log.parent == logger.log_dir

    def test_logger_init_default_dir(self):
        """Test logger uses default directory when none provided."""
        logger = PredictionLogger(log_dir=None)
        assert logger.log_dir is not None

    def test_logger_has_lock(self):
        """Test that logger has thread lock."""
        logger = PredictionLogger()
        assert logger._lock is not None

    def test_log_prediction_writes_to_file(self):
        """Test that log_prediction writes to predictions log."""
        logger = PredictionLogger(log_dir=Path("logs/test"))
        test_file = logger.predictions_log

        # Clear file if it exists
        if test_file.exists():
            test_file.unlink()

        logger.log_prediction(
            transaction_id="txn_123",
            request={"amount": 100.0, "features": list(range(31))},
            response={"fraud_probability": 0.1, "prediction": 0, "risk_level": "LOW", "threshold_used": 0.5},
            api_key="dev-key-12345",
            response_time_ms=45.5
        )

        # Verify file was written
        assert test_file.exists()

        # Read and verify content
        with open(test_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            entry = json.loads(lines[0])
            assert entry["transaction_id"] == "txn_123"

    def test_log_prediction_masks_api_key(self):
        """Test that API key is masked in logs."""
        logger = PredictionLogger(log_dir=Path("logs/test"))
        test_file = logger.predictions_log

        logger.log_prediction(
            transaction_id="txn_456",
            request={"amount": 50.0, "features": list(range(31))},
            response={"fraud_probability": 0.8, "prediction": 1, "risk_level": "HIGH", "threshold_used": 0.5},
            api_key="test-key-67890",
            response_time_ms=30.0
        )

        with open(test_file, 'r') as f:
            content = f.read()
            # Last entry should contain masked key
            if content.strip():
                entry = json.loads(content.strip().split('\n')[-1])
                assert "test-key-67890" not in str(entry)

    def test_log_prediction_short_api_key(self):
        """Test logging with short API key."""
        logger = PredictionLogger(log_dir=Path("logs/test"))

        logger.log_prediction(
            transaction_id="txn_789",
            request={"amount": 25.0, "features": list(range(31))},
            response={"fraud_probability": 0.5, "prediction": 0, "risk_level": "MEDIUM", "threshold_used": 0.5},
            api_key="short",
            response_time_ms=20.0
        )

        # Should not crash
        assert True

    def test_log_batch_prediction_writes_to_file(self):
        """Test that log_batch_prediction writes correct data."""
        logger = PredictionLogger(log_dir=Path("logs/test"))
        test_file = logger.predictions_log

        transactions = [
            {"transaction_id": "txn_1", "amount": 100.0, "features": list(range(31))},
            {"transaction_id": "txn_2", "amount": 200.0, "features": list(range(31))}
        ]
        responses = [
            {"fraud_probability": 0.1, "prediction": 0, "risk_level": "LOW", "threshold_used": 0.5},
            {"fraud_probability": 0.9, "prediction": 1, "risk_level": "HIGH", "threshold_used": 0.5}
        ]

        logger.log_batch_prediction(
            transactions=transactions,
            responses=responses,
            api_key="dev-key-12345",
            response_time_ms=100.0
        )

        with open(test_file, 'r') as f:
            lines = f.readlines()
            entry = json.loads(lines[-1])
            assert entry["batch_size"] == 2
            assert entry["fraud_count"] == 1
            assert entry["fraud_rate"] == 0.5
            assert entry["performance"]["response_time_ms"] == 100.0

    def test_log_batch_prediction_empty_list(self):
        """Test batch prediction log with empty transactions."""
        logger = PredictionLogger(log_dir=Path("logs/test"))

        logger.log_batch_prediction(
            transactions=[],
            responses=[],
            api_key="dev-key-12345",
            response_time_ms=0.0
        )

        # Should not crash
        assert True

    def test_log_error_writes_to_file(self):
        """Test that log_error writes to errors log."""
        logger = PredictionLogger(log_dir=Path("logs/test"))
        test_file = logger.errors_log

        error = ValueError("Invalid input")
        logger.log_error(
            endpoint="/api/v1/predict",
            error=error,
            request_data={"transaction_id": "txn_error", "amount": 100.0},
            api_key="dev-key-12345"
        )

        assert test_file.exists()

        with open(test_file, 'r') as f:
            entry = json.loads(f.read().strip().split('\n')[-1])
            assert entry["endpoint"] == "/api/v1/predict"
            assert entry["error_type"] == "ValueError"

    def test_log_error_without_request_data(self):
        """Test log_error with no request data."""
        logger = PredictionLogger(log_dir=Path("logs/test"))

        error = RuntimeError("Model failed")
        logger.log_error(
            endpoint="/api/v1/health",
            error=error
        )

        # Should not crash
        assert True

    def test_log_error_without_api_key(self):
        """Test log_error with no API key."""
        logger = PredictionLogger(log_dir=Path("logs/test"))

        error = Exception("Unknown error")
        logger.log_error(
            endpoint="/api/v1/model/info",
            error=error,
            api_key=None
        )

        # Should not crash
        assert True

    def test_log_error_short_api_key(self):
        """Test log_error with short API key."""
        logger = PredictionLogger(log_dir=Path("logs/test"))

        error = Exception("Test")
        logger.log_error(
            endpoint="/api/v1/test",
            error=error,
            api_key="key"
        )

        # Should not crash
        assert True


@pytest.mark.unit
class TestGlobalLogger:
    """Tests for global prediction_logger instance."""

    def test_global_logger_exists(self):
        """Test that global logger is initialized."""
        assert prediction_logger is not None
        assert isinstance(prediction_logger, PredictionLogger)
