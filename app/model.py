"""
Model Service - Handles ML model loading and predictions

Key Concepts:
1. Singleton Pattern: Load model ONCE at startup, not per request
2. Lazy Loading: Load model only when first needed
3. Thread Safety: Model is read-only, safe for concurrent requests
"""
import joblib
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import logging

from app.config import MODEL_PATH, MODEL_METADATA_PATH, RISK_LEVELS, DEFAULT_THRESHOLD

logger = logging.getLogger(__name__)


class ModelService:
    """
    Singleton service for ML model predictions.

    Why Singleton?
    - Models are large (MBs to GBs) - load once, use many times
    - Thread-safe for concurrent API requests
    - Memory efficient
    """
    _instance = None
    _model = None
    _metadata = None

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("ModelService instance created")
        return cls._instance

    def __init__(self):
        """Initialize the service (lazy loading)."""
        if self._model is None:
            self._load_model()

    def _load_model(self) -> None:
        """
        Load the trained model and metadata.

        Called once on first use.
        """
        try:
            logger.info(f"Loading model from {MODEL_PATH}")
            self._model = joblib.load(MODEL_PATH)
            logger.info("Model loaded successfully")

            # Load metadata
            if MODEL_METADATA_PATH.exists():
                with open(MODEL_METADATA_PATH, 'r') as f:
                    self._metadata = json.load(f)
                logger.info("Model metadata loaded")
            else:
                self._metadata = {}
                logger.warning("Model metadata not found")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Model loading failed: {e}")

    @property
    def model(self):
        """Get the loaded model (raises error if not loaded)."""
        if self._model is None:
            raise RuntimeError("Model not loaded")
        return self._model

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get model metadata."""
        return self._metadata or {}

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get comprehensive model information.

        Returns:
            Dict with model name, version, training date, etc.
        """
        info = {
            "model_name": self.metadata.get("model_name", "Fraud Detector"),
            "model_version": self.metadata.get("model_version", "1.0"),
            "algorithm": self.metadata.get("algorithm", "XGBoost"),
            "training_date": self.metadata.get("training_date", "Unknown"),
            "technique": self.metadata.get("technique", "baseline"),
            "feature_count": 31,  # V1-V28 + amount_scaled + hour_sin + hour_cos
            "threshold": DEFAULT_THRESHOLD
        }

        # Add performance metrics if available
        if "performance" in self.metadata:
            info["performance"] = self.metadata["performance"]

        return info

    def predict(
        self,
        features: List[float],
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        Make a fraud prediction for a single transaction.

        Args:
            features: List of 31 feature values
            threshold: Decision threshold (default: DEFAULT_THRESHOLD)

        Returns:
            Dict with fraud_probability, prediction, risk_level
        """
        if threshold is None:
            threshold = DEFAULT_THRESHOLD

        # Convert to numpy array and reshape for prediction
        X = np.array(features).reshape(1, -1)

        # Get probability of fraud (class 1)
        try:
            proba = self.model.predict_proba(X)[0, 1]
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise RuntimeError(f"Prediction failed: {e}")

        # Binary prediction
        prediction = int(proba >= threshold)

        # Determine risk level
        if proba >= RISK_LEVELS["HIGH"]:
            risk_level = "HIGH"
        elif proba >= RISK_LEVELS["MEDIUM"]:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "fraud_probability": float(proba),
            "prediction": prediction,
            "risk_level": risk_level,
            "threshold_used": threshold
        }

    def predict_batch(
        self,
        features_list: List[List[float]],
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Make predictions for multiple transactions.

        More efficient than calling predict() multiple times.

        Args:
            features_list: List of feature arrays
            threshold: Decision threshold

        Returns:
            List of prediction dictionaries
        """
        if threshold is None:
            threshold = DEFAULT_THRESHOLD

        # Convert to numpy array
        X = np.array(features_list)

        # Get probabilities for all
        try:
            probabilities = self.model.predict_proba(X)[:, 1]
        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            raise RuntimeError(f"Batch prediction failed: {e}")

        results = []
        for proba in probabilities:
            prediction = int(proba >= threshold)

            if proba >= RISK_LEVELS["HIGH"]:
                risk_level = "HIGH"
            elif proba >= RISK_LEVELS["MEDIUM"]:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            results.append({
                "fraud_probability": float(proba),
                "prediction": prediction,
                "risk_level": risk_level,
                "threshold_used": threshold
            })

        return results

    def health_check(self) -> bool:
        """
        Check if model is loaded and ready.

        Returns:
            True if model is loaded and usable
        """
        return self._model is not None


# Global service instance (created on first import)
model_service = ModelService()
