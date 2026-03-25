"""
Request Logging Module

Logs all API requests for audit, debugging, and analytics.

Features:
- Dual logging: JSONL files + PostgreSQL (optional)
- Thread-safe writes
- Timestamp, API key, transaction ID tracking
- Performance metrics (response time)
- Graceful fallback if database unavailable
"""
import logging
import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import BASE_DIR, ENABLE_DB_LOGGING

# Database config for psycopg2
import os
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "fraud_detection"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Database availability check
try:
    import psycopg2
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    ENABLE_DB_LOGGING = True


logger = logging.getLogger("api")


class PredictionLogger:
    """
    Thread-safe logger for prediction requests.

    Supports dual logging:
    1. File logging (JSONL) - always available
    2. Database logging (PostgreSQL) - optional, graceful fallback
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

        # Log files (always available)
        self.predictions_log = self.log_dir / "predictions.jsonl"
        self.errors_log = self.log_dir / "errors.jsonl"

        # Thread lock for safe concurrent writes
        self._lock = threading.Lock()

        # Check database connectivity (if enabled)
        if ENABLE_DB_LOGGING and DB_AVAILABLE:
            self._init_database()

        # Setup standard logger for general logging
        self._setup_logger()

    def _init_database(self) -> bool:
        """
        Initialize database connection using psycopg2 directly.

        Returns:
            bool: True if database is accessible
        """
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                database=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                connect_timeout=5
            )
            conn.close()
            logger.info(f"Database connection verified: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            return True
        except Exception as e:
            logger.error(f"Database initialization failed: {type(e).__name__}: {e}")
            logger.error(f"DB_CONFIG: host={DB_CONFIG['host']}, port={DB_CONFIG['port']}, database={DB_CONFIG['database']}, user={DB_CONFIG['user']}")
            return False

    def _setup_logger(self):
        """Configure Python logging module."""
        logger.setLevel(logging.INFO)

        # Console handler
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    def _log_features_for_drift(
        self,
        transaction_id: str,
        features: list
    ) -> bool:
        """
        Log input features to prediction_inputs table for drift monitoring.

        This is independent from predictions_log - if this fails, main logging continues.

        Args:
            transaction_id: Transaction identifier
            features: List of 28 feature values (V1-V28)

        Returns:
            bool: True if successful
        """
        if not DB_AVAILABLE:
            return False

        try:
            import psycopg2

            conn = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                database=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                connect_timeout=5
            )
            cursor = conn.cursor()

            # Build column names and placeholders
            columns = ["transaction_id"] + [f"v{i}" for i in range(1, 29)]
            placeholders = ["%s"] * 29
            sql = f"""
                INSERT INTO prediction_inputs
                ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """

            params = [str(transaction_id)[:50]] + [float(f) for f in features[:28]]
            # Pad with zeros if fewer than 28 features
            params.extend([0.0] * (28 - len(features[:28])))

            cursor.execute(sql, params)
            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            # Don't fail the main prediction if drift logging fails
            logger.debug(f"Feature drift logging failed (non-critical): {type(e).__name__}: {e}")
            return False

    def _log_to_database(
        self,
        table_name: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Log prediction or error to database using psycopg2 directly.

        Uses psycopg2 instead of SQLAlchemy for reliability.
        """
        if not DB_AVAILABLE:
            return False

        if table_name not in ('predictions_log', 'error_logs'):
            return False

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                database=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                connect_timeout=5
            )
            cursor = conn.cursor()

            sql = """
                INSERT INTO predictions_log
                (transaction_id, prediction, confidence, risk_level, model_version, latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                str(data.get('transaction_id', ''))[:50],  # Limit to varchar(50)
                int(data.get('prediction', 0)),
                float(data.get('confidence', 0.0)),
                str(data.get('risk_level', 'UNKNOWN'))[:10],
                str(data.get('model_version', 'v1.0'))[:50],
                float(data.get('latency_ms', 0.0))
            )

            cursor.execute(sql, params)
            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Database logging failed: {type(e).__name__}: {e}")
            return False

    def _log_to_file(self, file_path: Path, log_entry: Dict[str, Any]) -> bool:
        """
        Log entry to JSONL file.

        Args:
            file_path: Path to log file
            log_entry: Dictionary to log as JSON

        Returns:
            bool: True if successful
        """
        try:
            with open(file_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            return True
        except Exception as e:
            logger.error(f"Failed to write to {file_path}: {e}")
            return False

    def log_prediction(
        self,
        transaction_id: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
        api_key: str,
        response_time_ms: float,
        features: Optional[list] = None
    ) -> None:
        """
        Log a prediction request and response.

        Writes to BOTH database and file (dual logging).

        Args:
            transaction_id: Transaction identifier
            request: Request data (features, amount, etc.)
            response: Prediction result (probability, prediction, etc.)
            api_key: Client API key (masked)
            response_time_ms: Request processing time in milliseconds
            features: Optional list of feature values (V1-V28) for drift monitoring
        """
        # Prepare log data - matches existing EC2 schema
        db_data = {
            "transaction_id": transaction_id[:50],  # Limit to varchar(50)
            "confidence": response.get("fraud_probability"),
            "prediction": response.get("prediction"),
            "risk_level": response.get("risk_level"),
            "model_version": "v1.0",
            "latency_ms": round(response_time_ms, 2)
        }

        # File log entry (with full structure for debugging)
        file_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction_id": transaction_id,
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

        # Thread-safe dual write
        with self._lock:
            # Always log to file (fallback guaranteed)
            self._log_to_file(self.predictions_log, file_entry)

            # Also log to database if enabled and available
            if ENABLE_DB_LOGGING and DB_AVAILABLE:
                self._log_to_database('predictions_log', db_data)

            # Log input features for drift monitoring (independent, non-critical)
            if features is not None and ENABLE_DB_LOGGING and DB_AVAILABLE:
                self._log_features_for_drift(transaction_id, features)

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

        file_entry = {
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
            self._log_to_file(self.predictions_log, file_entry)
            # Note: Batch predictions not stored individually to DB
            # Each transaction in batch should be logged via log_prediction

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
        # Prepare data for database
        db_data = {
            "endpoint": endpoint,
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],  # Limit length
            "transaction_id": request_data.get("transaction_id") if request_data else None,
            "amount": request_data.get("amount") if request_data else None,
            "api_key_prefix": api_key[:8] + "..." if api_key and len(api_key) > 8 else None
        }

        # File entry (with full structure)
        file_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **db_data
        }

        # Add request data to file entry
        if request_data:
            file_entry["request"] = {
                "transaction_id": request_data.get("transaction_id"),
                "amount": request_data.get("amount")
            }

        with self._lock:
            # Always log to file
            self._log_to_file(self.errors_log, file_entry)

            # Also log to database if enabled
            if ENABLE_DB_LOGGING and DB_AVAILABLE:
                self._log_to_database('error_logs', db_data)

    def health_check(self) -> Dict[str, Any]:
        """
        Check logging system health.

        Returns:
            Dict with health status
        """
        # Check if database is accessible
        db_healthy = False
        if DB_AVAILABLE and ENABLE_DB_LOGGING:
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=DB_CONFIG["host"],
                    port=DB_CONFIG["port"],
                    database=DB_CONFIG["database"],
                    user=DB_CONFIG["user"],
                    password=DB_CONFIG["password"],
                    connect_timeout=3
                )
                conn.close()
                db_healthy = True
            except:
                pass

        return {
            "file_logging": "healthy",
            "db_logging": "healthy" if db_healthy else "disabled",
            "db_connected": db_healthy
        }


# Global logger instance
prediction_logger = PredictionLogger()
