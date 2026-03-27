"""
Model Service Tests

Tests for ModelService class including prediction logic,
model loading, and error handling.
"""
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from app.model import ModelService, model_service


@pytest.mark.unit
class TestModelServiceSingleton:
    """Tests for ModelService singleton pattern."""

    def test_model_service_singleton(self):
        """Test that ModelService returns the same instance."""
        service1 = ModelService()
        service2 = ModelService()

        # Should be the same instance (singleton)
        assert id(service1) == id(service2)

    def test_global_model_service_is_instance(self):
        """Test that global model_service is a ModelService instance."""
        assert isinstance(model_service, ModelService)


@pytest.mark.unit
class TestModelServiceHealthCheck:
    """Tests for model health check functionality."""

    def test_health_check_returns_bool(self):
        """Test that health_check returns a boolean."""
        result = model_service.health_check()
        assert isinstance(result, bool)

    def test_health_check_true_when_model_loaded(self):
        """Test that health_check returns True when model is loaded."""
        # Model should be loaded at import time
        assert model_service.health_check() is True


@pytest.mark.unit
class TestModelServiceGetModelInfo:
    """Tests for model information retrieval."""

    def test_get_model_info_returns_dict(self):
        """Test that get_model_info returns a dictionary."""
        info = model_service.get_model_info()
        assert isinstance(info, dict)

    def test_get_model_info_has_required_keys(self):
        """Test that model info contains all required keys."""
        info = model_service.get_model_info()

        required_keys = ["model_name", "model_version", "algorithm", "feature_count"]
        for key in required_keys:
            assert key in info

    def test_get_model_info_feature_count_is_31(self):
        """Test that feature count is 31 (V1-V28 + amount_scaled + hour_sin + hour_cos)."""
        info = model_service.get_model_info()
        assert info["feature_count"] == 31


@pytest.mark.unit
class TestModelServicePredict:
    """Tests for single prediction functionality."""

    def test_predict_returns_dict(self, sample_features):
        """Test that predict returns a dictionary."""
        result = model_service.predict(sample_features)
        assert isinstance(result, dict)

    def test_predict_has_required_keys(self, sample_features):
        """Test that prediction result contains all required keys."""
        result = model_service.predict(sample_features)

        required_keys = ["fraud_probability", "prediction", "risk_level", "threshold_used"]
        for key in required_keys:
            assert key in result

    def test_predict_fraud_probability_in_range(self, sample_features):
        """Test that fraud_probability is between 0 and 1."""
        result = model_service.predict(sample_features)
        assert 0.0 <= result["fraud_probability"] <= 1.0

    def test_predict_prediction_is_binary(self, sample_features):
        """Test that prediction is either 0 or 1."""
        result = model_service.predict(sample_features)
        assert result["prediction"] in [0, 1]

    def test_predict_risk_level_is_valid(self, sample_features):
        """Test that risk_level is one of: HIGH, MEDIUM, LOW."""
        result = model_service.predict(sample_features)
        assert result["risk_level"] in ["HIGH", "MEDIUM", "LOW"]

    def test_predict_with_custom_threshold(self, sample_features):
        """Test that custom threshold is used in prediction."""
        result = model_service.predict(sample_features, threshold=0.7)
        assert result["threshold_used"] == 0.7

    def test_predict_default_threshold_0_5(self, sample_features):
        """Test that default threshold is 0.5."""
        result = model_service.predict(sample_features)
        assert result["threshold_used"] == 0.5

    def test_predict_risk_levels_match_thresholds(self, sample_features):
        """Test that risk levels correspond to probability thresholds."""
        # Test with known low probability
        result = model_service.predict(sample_features)
        prob = result["fraud_probability"]
        risk = result["risk_level"]

        # Verify risk level matches probability
        if prob >= 0.7:
            assert risk == "HIGH"
        elif prob >= 0.3:
            assert risk == "MEDIUM"
        else:
            assert risk == "LOW"


@pytest.mark.unit
class TestModelServicePredictBatch:
    """Tests for batch prediction functionality."""

    def test_predict_batch_returns_list(self, sample_features):
        """Test that predict_batch returns a list."""
        features_list = [sample_features] * 3
        results = model_service.predict_batch(features_list)
        assert isinstance(results, list)

    def test_predict_batch_length_matches_input(self, sample_features):
        """Test that batch prediction returns same number of results as inputs."""
        features_list = [sample_features] * 5
        results = model_service.predict_batch(features_list)
        assert len(results) == 5

    def test_predict_batch_all_dicts(self, sample_features):
        """Test that all batch results are dictionaries."""
        features_list = [sample_features] * 3
        results = model_service.predict_batch(features_list)

        for result in results:
            assert isinstance(result, dict)

    def test_predict_batch_with_threshold(self, sample_features):
        """Test that custom threshold works in batch predictions."""
        features_list = [sample_features] * 2
        results = model_service.predict_batch(features_list, threshold=0.8)

        for result in results:
            assert result["threshold_used"] == 0.8


@pytest.mark.unit
class TestModelServicePredictionConsistency:
    """Tests for prediction consistency and reproducibility."""

    def test_same_input_same_output(self, sample_features):
        """Test that identical inputs produce identical predictions."""
        result1 = model_service.predict(sample_features)
        result2 = model_service.predict(sample_features)

        assert result1["fraud_probability"] == result2["fraud_probability"]
        assert result1["prediction"] == result2["prediction"]
        assert result1["risk_level"] == result2["risk_level"]


@pytest.mark.unit
class TestModelServiceInputValidation:
    """Tests for input validation in predictions."""

    def test_predict_requires_31_features(self):
        """Test that predict raises error for wrong feature count."""
        wrong_features = list(range(30))  # Only 30 features

        with pytest.raises(RuntimeError):
            model_service.predict(wrong_features)

    def test_predict_batch_empty_list_raises_error(self):
        """Test that empty batch raises error."""
        with pytest.raises(RuntimeError):
            model_service.predict_batch([])


@pytest.mark.unit
class TestModelServiceErrorHandling:
    """Tests for error handling in ModelService."""

    def test_predict_with_nan_features(self):
        """Test behavior when features contain NaN values."""
        nan_features = [float('nan')] * 31

        # Model should handle this gracefully or raise an informative error
        try:
            result = model_service.predict(nan_features)
            # If it doesn't raise, result should still be valid
            assert result["prediction"] in [0, 1]
        except RuntimeError:
            # Also acceptable to raise an error
            pass

    def test_predict_with_inf_features(self):
        """Test behavior when features contain infinite values."""
        inf_features = [float('inf')] * 31

        try:
            result = model_service.predict(inf_features)
            assert result["prediction"] in [0, 1]
        except RuntimeError:
            pass
