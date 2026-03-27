"""
Automated Retraining Pipeline - Week 4 Day 4

This module implements the complete automated model retraining pipeline as specified
in project_guide.md Week 4 Day 4.

Pipeline Steps:
1. Trigger: Drift detected OR scheduled monthly OR manual override
2. Data: Pull latest 30-day window from transactions_raw table
3. Train: Execute full training pipeline with existing hyperparameters
4. Validate: New model must meet or exceed current model on holdout metrics
5. Promote: If validated, update model artifact and increment version
6. Deploy: Signal API to load new model (zero-downtime ready)
7. Notify: Send deployment notification with metrics comparison

Reference: project_guide.md Week 4 - Monitoring, Observability & Drift Detection
"""

import os
import json
import shutil
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
import pandas as pd
import joblib
import psycopg2
from psycopg2.extras import RealDictCursor

# Import existing modules
# Handle both local development (src/) and EC2 deployment (current directory)
try:
    # EC2: files in current directory
    from alerting import EmailAlerter, log_alert_to_db, get_db_connection
except ImportError:
    # Local: files in src/ directory
    from src.alerting import EmailAlerter, log_alert_to_db, get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "fraud_detection"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Model paths
MODELS_DIR = Path("models")
CURRENT_MODEL_PATH = MODELS_DIR / "fraud_detector_v1.pkl"
CURRENT_METADATA_PATH = MODELS_DIR / "metadata.json"

# Validation thresholds (per project_guide.md)
VALIDATION_THRESHOLDS = {
    "min_roc_auc": 0.95,
    "min_recall": 0.85,
    "min_precision": 0.85,
    "relative_improvement": 0.0,  # 0% = must not degrade, can be equal
}

# Feature columns expected by the model
FEATURE_COLUMNS = [
    "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10",
    "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v19", "v20",
    "v21", "v22", "v23", "v24", "v25", "v26", "v27", "v28",
    "hour_sin", "hour_cos", "amount_scaled"
]

# Data window for retraining (default: 30 days)
DEFAULT_DATA_WINDOW_DAYS = 30


# ============================================================================
# RETRAINING LOG DATABASE TABLE
# ============================================================================

def create_retraining_table() -> bool:
    """
    Create the retraining_log table if it doesn't exist.

    This table tracks all retraining runs with their outcomes.

    Returns:
        bool: True if table created or already exists
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            CREATE TABLE IF NOT EXISTS retraining_log (
                id SERIAL PRIMARY KEY,
                run_id VARCHAR(50) UNIQUE NOT NULL,
                triggered_by VARCHAR(50) NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                status VARCHAR(20) NOT NULL,
                data_rows INTEGER,
                data_window_days INTEGER,

                -- Model metrics
                roc_auc FLOAT,
                precision FLOAT,
                recall FLOAT,
                f1_score FLOAT,

                -- Comparison with baseline
                baseline_roc_auc FLOAT,
                baseline_precision FLOAT,
                baseline_recall FLOAT,

                -- Validation result
                validation_passed BOOLEAN,
                promoted BOOLEAN DEFAULT FALSE,
                new_model_version VARCHAR(50),

                -- Error tracking
                error_message TEXT,

                -- Additional metadata
                metadata JSONB,

                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_retraining_run_id ON retraining_log(run_id);
            CREATE INDEX IF NOT EXISTS idx_retraining_status ON retraining_log(status);
            CREATE INDEX IF NOT EXISTS idx_retraining_started_at ON retraining_log(started_at DESC);
        """

        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()

        logger.info("Retraining log table verified/created")
        return True

    except Exception as e:
        logger.error(f"Failed to create retraining_log table: {e}")
        return False


def log_retraining_start(
    run_id: str,
    triggered_by: str,
    data_window_days: int,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Log the start of a retraining run."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO retraining_log (
                run_id, triggered_by, started_at, status,
                data_window_days, metadata
            ) VALUES (%s, %s, NOW(), %s, %s, %s)
        """

        cursor.execute(query, (
            run_id,
            triggered_by,
            "running",
            data_window_days,
            json.dumps(metadata) if metadata else None
        ))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Retraining run {run_id} logged to database")
        return True

    except Exception as e:
        logger.error(f"Failed to log retraining start: {e}")
        return False


def log_retraining_completion(
    run_id: str,
    status: str,
    metrics: Optional[Dict[str, float]] = None,
    baseline_metrics: Optional[Dict[str, float]] = None,
    validation_passed: Optional[bool] = None,
    promoted: bool = False,
    new_model_version: Optional[str] = None,
    error_message: Optional[str] = None,
    data_rows: Optional[int] = None
) -> bool:
    """Log the completion of a retraining run."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            UPDATE retraining_log
            SET
                completed_at = NOW(),
                status = %s,
                data_rows = %s,
                roc_auc = %s,
                precision = %s,
                recall = %s,
                f1_score = %s,
                baseline_roc_auc = %s,
                baseline_precision = %s,
                baseline_recall = %s,
                validation_passed = %s,
                promoted = %s,
                new_model_version = %s,
                error_message = %s
            WHERE run_id = %s
        """

        cursor.execute(query, (
            status,
            data_rows,
            metrics.get("roc_auc") if metrics else None,
            metrics.get("precision") if metrics else None,
            metrics.get("recall") if metrics else None,
            metrics.get("f1") if metrics else None,
            baseline_metrics.get("roc_auc") if baseline_metrics else None,
            baseline_metrics.get("precision") if baseline_metrics else None,
            baseline_metrics.get("recall") if baseline_metrics else None,
            validation_passed,
            promoted,
            new_model_version,
            error_message,
            run_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Retraining run {run_id} completion logged")
        return True

    except Exception as e:
        logger.error(f"Failed to log retraining completion: {e}")
        return False


# ============================================================================
# DATA LOADING FOR RETRAINING
# ============================================================================

def load_training_data_from_db(
    window_days: int = DEFAULT_DATA_WINDOW_DAYS,
    max_rows: Optional[int] = 100000
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load training data from PostgreSQL transactions_training table.

    Uses chunked fetching with psycopg2 to avoid hanging on EC2 with large datasets.
    Per project_guide.md Week 4 Day 4: "Pull latest 30-day window from transactions_features table"
    Note: Using transactions_training table which has features + labels for supervised learning.

    IMPORTANT: Uses OFFSET/LIMIT pagination to fetch data in chunks (5000 rows at a time)
    to avoid memory overload on t3.medium (4GB RAM). cursor.fetchall() with 284K rows causes hang.

    DEFAULT max_rows=100000: This limit prevents memory overflow on t3.medium (4GB RAM) while
    providing sufficient data for training (~170 fraud cases at 0.17% rate). Override by
    passing larger value if using instance with more RAM (e.g., t3.large with 8GB).

    Args:
        window_days: Number of days to look back for data
        max_rows: Maximum rows to load (default: 100000 for t3.medium compatibility)

    Returns:
        Tuple of (DataFrame with training data, data_info dict)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calculate cutoff date for time window
        cutoff_date = datetime.now() - timedelta(days=window_days)

        # First, get total count to log progress
        count_query = """
            SELECT COUNT(*) FROM transactions_training
            WHERE ingested_at >= %s
        """
        cursor.execute(count_query, (cutoff_date,))
        total_rows = cursor.fetchone()[0]

        if max_rows and total_rows > max_rows:
            total_rows = max_rows

        logger.info(f"Total rows to load: {total_rows}")

        # Column names for the DataFrame
        column_names = [
            'time_elapsed', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10',
            'v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20',
            'v21', 'v22', 'v23', 'v24', 'v25', 'v26', 'v27', 'v28',
            'amount', 'amount_scaled', 'hour_sin', 'hour_cos', 'class'
        ]

        # Process in chunks to avoid memory overload
        CHUNK_SIZE = 5000
        offset = 0
        all_rows = []
        processed = 0

        while offset < total_rows:
            logger.info(f"Fetching rows {offset} to {offset + CHUNK_SIZE}...")

            # Query with OFFSET/LIMIT for chunked fetching
            query = """
                SELECT
                    time_elapsed,
                    v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
                    v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
                    v21, v22, v23, v24, v25, v26, v27, v28,
                    amount, amount_scaled, hour_sin, hour_cos, class
                FROM transactions_training
                WHERE ingested_at >= %s
                ORDER BY id
                LIMIT %s OFFSET %s
            """

            cursor.execute(query, (cutoff_date, CHUNK_SIZE, offset))
            rows = cursor.fetchall()

            if not rows:
                break

            all_rows.extend(rows)
            processed += len(rows)

            logger.info(f"Progress: {processed}/{total_rows} rows ({processed*100//total_rows}%)")

            offset += CHUNK_SIZE

        cursor.close()
        conn.close()

        # Create DataFrame from fetched rows
        df = pd.DataFrame(all_rows, columns=column_names)

        data_info = {
            "rows_loaded": len(df),
            "fraud_cases": int(df["class"].sum()),
            "fraud_rate": float(df["class"].mean()),
            "window_days": window_days,
            "cutoff_date": cutoff_date.isoformat(),
        }

        logger.info(f"Loaded {len(df)} rows from transactions_training (fraud rate: {data_info['fraud_rate']:.4%})")
        logger.info(f"Data window: last {window_days} days (since {cutoff_date.strftime('%Y-%m-%d')})")

        return df, data_info

    except Exception as e:
        logger.error(f"Failed to load data from database: {e}")
        raise


def prepare_features_for_training(df: pd.DataFrame) -> Tuple:
    """
    Prepare features for model training.

    Since we pull from transactions_training, the features are already engineered.
    Just need to split into train/test sets.

    Args:
        df: Data from transactions_training (already has engineered features + labels)

    Returns:
        Tuple of (X_train, X_val, X_test, y_train, y_val, y_test, None)
    """
    from sklearn.model_selection import train_test_split

    # Features are already engineered in transactions_features table
    feature_cols = [
        "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10",
        "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v19", "v20",
        "v21", "v22", "v23", "v24", "v25", "v26", "v27", "v28",
        "hour_sin", "hour_cos", "amount_scaled"
    ]

    X = df[feature_cols].values
    y = df['class'].values

    # Stratified train/test split (70/15/15 per project_guide)
    # First split: 70% train, 30% temp
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Second split: 15% val, 15% test (from temp)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )

    logger.info(f"Train: {len(X_train):,}, Val: {len(X_val):,}, Test: {len(X_test):,}")

    # Return None for scaler since features are already scaled
    return X_train, X_val, X_test, y_train, y_val, y_test, None


# ============================================================================
# MODEL TRAINING WITH EXISTING HYPERPARAMETERS
# ============================================================================

def get_current_model_hyperparameters() -> Dict[str, Any]:
    """
    Load hyperparameters from the current production model.

    Returns:
        Dict of hyperparameters (or defaults if not found)
    """
    # Default hyperparameters from Optuna training
    default_params = {
        'max_depth': 6,
        'learning_rate': 0.05,
        'n_estimators': 300,
        'min_child_weight': 3,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 0.1,
        'reg_lambda': 0.1,
        'scale_pos_weight': 578.0,
        'random_state': 42,
        'n_jobs': -1,
        'eval_metric': 'logloss',
    }

    # Try to load from saved study
    study_path = MODELS_DIR / "optuna_study.pkl"
    if study_path.exists():
        try:
            study = joblib.load(study_path)
            if study.best_params:
                default_params.update(study.best_params)
                logger.info("Loaded hyperparameters from Optuna study")
        except Exception as e:
            logger.warning(f"Could not load Optuna study: {e}")

    return default_params


def train_model_with_hyperparameters(
    X_train: np.ndarray,
    y_train: np.ndarray,
    hyperparameters: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Train XGBoost model with specified hyperparameters.

    Args:
        X_train: Training features
        y_train: Training labels
        hyperparameters: Model hyperparameters (uses defaults if None)

    Returns:
        Trained XGBoost model
    """
    from xgboost import XGBClassifier

    params = hyperparameters or get_current_model_hyperparameters()

    logger.info("Training XGBoost model with hyperparameters:")
    for key, value in params.items():
        if isinstance(value, float):
            logger.info(f"  {key}: {value:.4f}")
        else:
            logger.info(f"  {key}: {value}")

    model = XGBClassifier(**params)
    model.fit(X_train, y_train)

    logger.info("Model training completed")
    return model


# ============================================================================
# MODEL VALIDATION
# ============================================================================

def evaluate_model(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Dict[str, float]:
    """
    Evaluate model performance on test set.

    Args:
        model: Trained model
        X_test: Test features
        y_test: Test labels

    Returns:
        Dict with evaluation metrics
    """
    from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn)
    }

    return metrics


def validate_model(
    new_metrics: Dict[str, float],
    baseline_metrics: Dict[str, float]
) -> Tuple[bool, str, List[str]]:
    """
    Validate new model against baseline metrics.

    Per project_guide.md: "New model must meet or exceed current model on holdout metrics"

    Args:
        new_metrics: New model metrics
        baseline_metrics: Current production model metrics

    Returns:
        Tuple of (passed: bool, reason: str, details: list)
    """
    reasons = []
    details = []

    # Check minimum thresholds (per project_guide.md KPIs)
    checks = [
        ("ROC-AUC", new_metrics["roc_auc"], VALIDATION_THRESHOLDS["min_roc_auc"]),
        ("Recall", new_metrics["recall"], VALIDATION_THRESHOLDS["min_recall"]),
        ("Precision", new_metrics["precision"], VALIDATION_THRESHOLDS["min_precision"]),
    ]

    all_min_passed = True
    for name, value, threshold in checks:
        passed = value >= threshold
        all_min_passed = all_min_passed and passed
        status = "PASS" if passed else "FAIL"
        details.append(f"  {name}: {value:.4f} >= {threshold:.2f} [{status}]")

    if not all_min_passed:
        return False, "Model does not meet minimum KPI thresholds", details

    # Check relative improvement (must not degrade)
    improvements = []
    total_change = 0
    count = 0

    for metric_name in ["roc_auc", "recall", "precision"]:
        new_val = new_metrics.get(metric_name, 0)
        base_val = baseline_metrics.get(metric_name, 0)
        if base_val > 0:
            change = (new_val - base_val) / base_val
            total_change += change
            count += 1
            status = "+" if change >= 0 else ""
            improvements.append(f"  {metric_name}: {new_val:.4f} ({status}{change:.2%})")

    avg_change = total_change / count if count > 0 else 0

    details.append(f"\nComparison vs baseline:")
    details.extend(improvements)
    details.append(f"  Average change: {avg_change:+.2%}")

    # Pass if not degraded (avg change >= 0)
    if avg_change >= VALIDATION_THRESHOLDS["relative_improvement"]:
        return True, f"Model validated (avg change: {avg_change:+.2%})", details
    else:
        return False, f"Model degraded (avg change: {avg_change:+.2%})", details


# ============================================================================
# MODEL PROMOTION & DEPLOYMENT
# ============================================================================

def get_next_model_version() -> str:
    """Generate next model version number."""
    # Check for existing model versions
    existing_versions = []
    for f in MODELS_DIR.glob("fraud_detector_v*.pkl"):
        if f.stem != "fraud_detector_v1" and "_backup" not in f.stem:
            try:
                num = int(f.stem.split("_v")[1])
                existing_versions.append(num)
            except (ValueError, IndexError):
                pass

    next_num = max(existing_versions) + 1 if existing_versions else 2
    return f"fraud_detector_v{next_num}"


def promote_model(
    model: Any,
    scaler: Any,
    metrics: Dict[str, float],
    hyperparameters: Dict[str, Any],
    run_id: str
) -> str:
    """
    Promote new model to production.

    Implements zero-downtime deployment strategy:
    1. Save new model with version suffix
    2. Update metadata.json with new model info
    3. Create backup for rollback capability
    4. Signal API can reload (handled separately)

    Args:
        model: Trained model
        scaler: Not used (features already scaled in transactions_features)
        metrics: Model evaluation metrics
        hyperparameters: Model hyperparameters
        run_id: Retraining run ID

    Returns:
        Path to promoted model
    """
    new_version = get_next_model_version()
    new_model_path = MODELS_DIR / f"{new_version}.pkl"

    # Backup current model
    backup_path = None
    if CURRENT_MODEL_PATH.exists():
        backup_path = MODELS_DIR / f"{CURRENT_MODEL_PATH.stem}_backup_{run_id[:8]}.pkl"
        shutil.copy2(CURRENT_MODEL_PATH, backup_path)
        logger.info(f"Backed up current model to: {backup_path}")

    # Save new model directly (features already pre-scaled in transactions_features)
    joblib.dump(model, new_model_path)

    # Update metadata.json
    metadata = {
        "model_name": f"Fraud Detector {new_version}",
        "version": new_version,
        "training_date": datetime.now().isoformat(),
        "run_id": run_id,
        "threshold": 0.5,
        "features": FEATURE_COLUMNS,
        "metrics": {
            "roc_auc": metrics["roc_auc"],
            "recall": metrics["recall"],
            "precision": metrics["precision"],
            "f1_score": metrics["f1"]
        },
        "hyperparameters": hyperparameters,
        "kpi_status": {
            "roc_auc_pass": metrics["roc_auc"] >= VALIDATION_THRESHOLDS["min_roc_auc"],
            "recall_pass": metrics["recall"] >= VALIDATION_THRESHOLDS["min_recall"],
            "precision_pass": metrics["precision"] >= VALIDATION_THRESHOLDS["min_precision"]
        },
        "backup_path": str(backup_path) if backup_path else None
    }

    with open(CURRENT_METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Update symlink/copy for current model
    if CURRENT_MODEL_PATH != new_model_path:
        shutil.copy2(new_model_path, CURRENT_MODEL_PATH)
        logger.info(f"Copied {new_model_path} to {CURRENT_MODEL_PATH}")

    logger.info(f"Model promoted to production: {new_version}")
    return new_version


def send_deployment_notification(
    run_id: str,
    new_version: str,
    new_metrics: Dict[str, float],
    baseline_metrics: Dict[str, float],
    triggered_by: str,
    validation_details: List[str]
) -> bool:
    """
    Send email notification about model deployment.

    Args:
        run_id: Retraining run ID
        new_version: New model version
        new_metrics: New model metrics
        baseline_metrics: Baseline metrics
        triggered_by: What triggered the retraining
        validation_details: Validation details list

    Returns:
        bool: True if notification sent
    """
    alerter = EmailAlerter()

    title = f"Model Deployed: {new_version}"

    # Calculate improvements
    improvements = []
    for metric in ["roc_auc", "recall", "precision"]:
        new_val = new_metrics.get(metric, 0)
        base_val = baseline_metrics.get(metric, 0)
        if base_val > 0:
            imp = (new_val - base_val) / base_val
            status = "+" if imp >= 0 else ""
            improvements.append(f"{metric}: {new_val:.4f} ({status}{imp:.2%})")

    message = f"""Model deployment completed successfully.

Run ID: {run_id}
New Version: {new_version}
Triggered By: {triggered_by}
Deployed At: {datetime.now().isoformat()}

New Model Metrics:
  ROC-AUC: {new_metrics['roc_auc']:.4f}
  Recall: {new_metrics['recall']:.4f}
  Precision: {new_metrics['precision']:.4f}
  F1 Score: {new_metrics['f1']:.4f}

Comparison vs Baseline:
{chr(10).join(improvements)}

The API will automatically load the new model on next request cycle.

Validation Details:
{chr(10).join(validation_details)}
"""

    details = {
        "run_id": run_id,
        "new_version": new_version,
        "triggered_by": triggered_by,
        "new_metrics": new_metrics,
        "baseline_metrics": baseline_metrics
    }

    email_sent = alerter.send_alert(
        alert_type="model_deployed",
        severity="info",
        title=title,
        message=message,
        details=details
    )

    log_alert_to_db(
        alert_type="model_deployed",
        severity="info",
        title=title,
        message=message,
        details=details,
        email_sent=email_sent
    )

    return email_sent


# ============================================================================
# MAIN RETRAINING PIPELINE
# ============================================================================

def generate_run_id() -> str:
    """Generate unique run ID for retraining job."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = hashlib.md5(os.urandom(4)).hexdigest()[:8]
    return f"retrain_{timestamp}_{random_suffix}"


def run_retraining_pipeline(
    triggered_by: str = "manual",
    data_window_days: int = DEFAULT_DATA_WINDOW_DAYS,
    force_promote: bool = False
) -> Dict[str, Any]:
    """
    Execute the complete automated retraining pipeline.

    Pipeline per project_guide.md Week 4 Day 4:
    1. Pull latest data from database
    2. Train new model with existing hyperparameters
    3. Validate against baseline
    4. Promote if validated
    5. Send notification

    Args:
        triggered_by: What triggered the retraining ('drift', 'scheduled', 'manual')
        data_window_days: Days of data to use for training
        force_promote: Skip validation and promote regardless

    Returns:
        Dict with pipeline results
    """
    run_id = generate_run_id()
    logger.info(f"Starting retraining pipeline: {run_id}")
    logger.info(f"Triggered by: {triggered_by}, Data window: {data_window_days} days")

    result = {
        "run_id": run_id,
        "triggered_by": triggered_by,
        "started_at": datetime.now().isoformat(),
        "status": "running"
    }

    # Ensure table exists
    create_retraining_table()

    # Log start
    log_retraining_start(run_id, triggered_by, data_window_days)

    try:
        # Step 1: Load training data
        logger.info("[1/6] Loading training data from database...")
        df, data_info = load_training_data_from_db(data_window_days)
        result["data_info"] = data_info

        # Step 2: Prepare features
        logger.info("[2/6] Preparing features...")
        X_train, X_val, X_test, y_train, y_val, y_test, scaler = prepare_features_for_training(df)
        result["data_split"] = {
            "train": len(X_train),
            "val": len(X_val),
            "test": len(X_test)
        }

        # Step 3: Load baseline metrics
        logger.info("[3/6] Loading baseline metrics...")
        baseline_metrics = {}
        if CURRENT_METADATA_PATH.exists():
            with open(CURRENT_METADATA_PATH) as f:
                metadata = json.load(f)
                baseline_metrics = metadata.get("metrics", {})
        else:
            logger.warning("No baseline metrics found, using defaults")
            baseline_metrics = {
                "roc_auc": 0.98,
                "recall": 0.85,
                "precision": 0.85
            }

        result["baseline_metrics"] = baseline_metrics

        # Step 4: Train new model
        logger.info("[4/6] Training new model...")
        hyperparameters = get_current_model_hyperparameters()
        new_model = train_model_with_hyperparameters(X_train, y_train, hyperparameters)

        # Step 5: Evaluate new model
        logger.info("[5/6] Evaluating new model...")
        new_metrics = evaluate_model(new_model, X_test, y_test)
        result["new_metrics"] = new_metrics

        logger.info(f"New Model Metrics:")
        logger.info(f"  ROC-AUC: {new_metrics['roc_auc']:.4f}")
        logger.info(f"  Recall: {new_metrics['recall']:.4f}")
        logger.info(f"  Precision: {new_metrics['precision']:.4f}")
        logger.info(f"  F1 Score: {new_metrics['f1']:.4f}")

        # Step 6: Validate against baseline
        logger.info("[6/6] Validating against baseline...")

        if force_promote:
            validation_passed = True
            validation_reason = "Force promote enabled - skipping validation"
            validation_details = ["Force promote: Validation skipped"]
        else:
            validation_passed, validation_reason, validation_details = validate_model(
                new_metrics, baseline_metrics
            )

        result["validation"] = {
            "passed": validation_passed,
            "reason": validation_reason,
            "details": validation_details
        }

        # Log validation details
        for detail in validation_details:
            logger.info(detail)

        # Step 7: Promote if validation passed
        if validation_passed:
            new_version = promote_model(
                new_model, scaler, new_metrics, hyperparameters, run_id
            )
            result["new_model_version"] = new_version
            result["promoted"] = True

            # Send notification
            send_deployment_notification(
                run_id, new_version, new_metrics, baseline_metrics,
                triggered_by, validation_details
            )

            result["status"] = "completed"
            logger.info(f"Retraining pipeline completed successfully: {new_version}")

        else:
            result["promoted"] = False
            result["status"] = "rejected"
            logger.warning(f"Retraining pipeline completed but model rejected: {validation_reason}")

            # Send rejection notification
            alerter = EmailAlerter()
            alerter.send_alert(
                alert_type="model_rejected",
                severity="warning",
                title=f"Model Rejected: {run_id}",
                message=f"New model did not pass validation.\n\nReason: {validation_reason}",
                details={"run_id": run_id, "metrics": new_metrics}
            )

        # Log completion
        log_retraining_completion(
            run_id=run_id,
            status=result["status"],
            metrics=new_metrics,
            baseline_metrics=baseline_metrics,
            validation_passed=validation_passed,
            promoted=result.get("promoted", False),
            new_model_version=result.get("new_model_version"),
            data_rows=data_info.get("rows_loaded")
        )

        result["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"Retraining pipeline failed: {e}")
        result["status"] = "failed"
        result["error"] = str(e)
        result["completed_at"] = datetime.now().isoformat()

        # Log failure
        log_retraining_completion(
            run_id=run_id,
            status="failed",
            error_message=str(e)
        )

        # Send failure alert
        alerter = EmailAlerter()
        alerter.send_alert(
            alert_type="retraining_failed",
            severity="critical",
            title=f"Retraining Failed: {run_id}",
            message=f"Automated retraining pipeline failed.\n\nError: {str(e)}",
            details={"run_id": run_id, "error": str(e)}
        )

    return result


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    """CLI entry point for manual retraining."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automated Retraining Pipeline - Fraud Detection System"
    )
    parser.add_argument(
        "--trigger",
        choices=["drift", "scheduled", "manual"],
        default="manual",
        help="What triggered the retraining"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DATA_WINDOW_DAYS,
        help=f"Data window in days (default: {DEFAULT_DATA_WINDOW_DAYS})"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force promotion without validation"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("     AUTOMATED RETRAINING PIPELINE")
    print("     project_guide.md Week 4 Day 4")
    print("=" * 70)
    print()
    print(f"Trigger: {args.trigger}")
    print(f"Data Window: {args.days} days")
    print(f"Force Promote: {args.force}")
    print(f"Started: {datetime.now().isoformat()}")
    print()

    result = run_retraining_pipeline(
        triggered_by=args.trigger,
        data_window_days=args.days,
        force_promote=args.force
    )

    print()
    print("-" * 70)
    print("RESULTS")
    print("-" * 70)
    print(f"Status: {result['status'].upper()}")
    print(f"Started: {result['started_at']}")

    if result['status'] == 'completed':
        print(f"New Version: {result.get('new_model_version', 'N/A')}")
        print(f"\nNew Model Metrics:")
        print(f"  ROC-AUC: {result['new_metrics']['roc_auc']:.4f}")
        print(f"  Recall: {result['new_metrics']['recall']:.4f}")
        print(f"  Precision: {result['new_metrics']['precision']:.4f}")
        print(f"  F1 Score: {result['new_metrics']['f1']:.4f}")
    elif result['status'] == 'rejected':
        print(f"Reason: {result['validation']['reason']}")
    elif result['status'] == 'failed':
        print(f"Error: {result.get('error', 'Unknown')}")

    print()


if __name__ == "__main__":
    main()
