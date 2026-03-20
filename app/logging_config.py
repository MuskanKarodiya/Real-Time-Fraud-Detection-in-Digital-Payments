"""
Request Logging Module

Logs all API requests for audit, debugging, and analytics.

Features:
- Structured JSON logging
- Separate log files for predictions and errors
- Timestamp, API key, transaction ID tracking
- Performance metrics (response time)
"""
import logging
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import threading

from app.config import BASE_DIR


class PredictionLogger:
    """
    Thread-safe logger for prediction requests.

    Why thread-safe?
    - FastAPI handles multiple requests concurrently
    - Multiple threads may write to log simultaneously
    - Lock ensures no data corruption
    """

    def __init__(self, log_dir: Path = None):
        """
        Initialize prediction logger.

        Args:
            log_dir: Directory for log files (default: BASE_DIR/logs)
        """
        if log_dir is None:
            log_dir = BASE_DIR / "logs"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Log files
        self.predictions_log = self.log_dir / "predictions.jsonl"
        self.errors_log = self.log_dir / "errors.jsonl"

        # Thread lock for safe concurrent writes
        self._lock = threading.Lock()

        # Setup standard logger for general logging
        self._setup_logger()

    def _setup_logger(self):
        """Configure Python logging module."""
        self.logger = logging.getLogger("api")
        self.logger.setLevel(logging.INFO)

        # Console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_prediction(
        self,
        transaction_id: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
        api_key: str,
        response_time_ms: float
    ) -> None:
        """
        Log a prediction request and response.

        Args:
            transaction_id: Transaction identifier
            request: Request data (features, amount, etc.)
            response: Prediction result (probability, prediction, etc.)
            api_key: Client API key (masked)
            response_time_ms: Request processing time in milliseconds
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction_id": transaction_id,
            "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "***",
            "request": {
                "amount": request.get("amount"),
                "feature_count": len(request.get("features", [])),
            },
            "response": {
                "fraud_probability": response.get("fraud_probability"),
                "prediction": response.get("prediction"),
                "risk_level": response.get("risk_level"),
                "threshold": response.get("threshold_used")
            },
            "performance": {
                "response_time_ms": round(response_time_ms, 2)
            }
        }

        # Thread-safe write
        with self._lock:
            try:
                with open(self.predictions_log, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                self.logger.error(f"Failed to write prediction log: {e}")

    def log_batch_prediction(
        self,
        transactions: list,
        responses: list,
        api_key: str,
        response_time_ms: float
    ) -> None:
        """
        Log a batch prediction request.

        Args:
            transactions: List of request data
            responses: List of prediction results
            api_key: Client API key (masked)
            response_time_ms: Request processing time
        """
        fraud_count = sum(r.get("prediction", 0) for r in responses)

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "***",
            "batch_size": len(transactions),
            "fraud_count": fraud_count,
            "fraud_rate": round(fraud_count / len(transactions), 4) if transactions else 0,
            "performance": {
                "response_time_ms": round(response_time_ms, 2),
                "avg_time_per_transaction": round(response_time_ms / len(transactions), 2) if transactions else 0
            }
        }

        with self._lock:
            try:
                with open(self.predictions_log, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                self.logger.error(f"Failed to write batch log: {e}")

    def log_error(
        self,
        endpoint: str,
        error: Exception,
        request_data: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None
    ) -> None:
        """
        Log an API error.

        Args:
            endpoint: The endpoint where error occurred
            error: The exception that was raised
            request_data: Relevant request data
            api_key: Client API key (masked)
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "api_key_prefix": api_key[:8] + "..." if api_key and len(api_key) > 8 else None
        }

        # Add request data if available (sanitize sensitive info)
        if request_data:
            log_entry["request"] = {
                "transaction_id": request_data.get("transaction_id"),
                "amount": request_data.get("amount")
            }

        with self._lock:
            try:
                with open(self.errors_log, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                self.logger.error(f"Failed to write error log: {e}")


# Global logger instance
prediction_logger = PredictionLogger()
