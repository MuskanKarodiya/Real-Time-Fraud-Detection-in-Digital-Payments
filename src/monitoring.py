"""
Monitoring Module

This module provides functionality for drift detection, alerting,
and model performance monitoring.

Reference: project_guide.md Week 4 - Monitoring, Observability & Drift Detection

Features implemented:
- Data drift detection (PSI, KS-test)
- Model performance tracking
- Alerting system (email)
- Performance degradation checks
- Automated retraining triggers
"""

import os
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS AND THRESHOLDS
# ============================================================================

# PSI Thresholds (per project_guide.md)
PSI_THRESHOLD_MIN = 0.1    # Moderate change - investigate
PSI_THRESHOLD_MAJOR = 0.2  # Significant change - alert

# KS Test Threshold
KS_P_VALUE_THRESHOLD = 0.05  # Alert if p-value < 0.05

# Performance Degradation Thresholds (per project_guide.md)
RECALL_THRESHOLD = 0.85
PRECISION_THRESHOLD = 0.85

# Alert Configuration
ALERT_LOG_FILE = Path("logs/alerts.jsonl")


# ============================================================================
# POPULATION STABILITY INDEX (PSI)
# ============================================================================

def calculate_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    bins: int = 10,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None
) -> float:
    """
    Calculate Population Stability Index (PSI) for a single feature.

    PSI measures how much a feature's distribution has changed since training.
    Formula: PSI = Σ[(Actual % - Expected %) × ln(Actual % / Expected %)]

    Args:
        expected: Training data distribution (reference)
        actual: Production data distribution (current)
        bins: Number of bins for discretization (default: 10)
        min_val: Minimum value for binning (uses data min if None)
        max_val: Maximum value for binning (uses data max if None)

    Returns:
        float: PSI value

    Interpretation:
        - PSI < 0.1: No significant change
        - 0.1 ≤ PSI < 0.2: Moderate change (investigate)
        - PSI ≥ 0.2: Significant change (alert!)
    """
    # Remove NaN values
    expected_clean = expected[~np.isnan(expected)]
    actual_clean = actual[~np.isnan(actual)]

    if len(expected_clean) == 0 or len(actual_clean) == 0:
        return 0.0

    # Determine bin edges from expected (training) data
    if min_val is None:
        min_val = expected_clean.min()
    if max_val is None:
        max_val = expected_clean.max()

    # Create bins
    bin_edges = np.linspace(min_val, max_val, bins + 1)

    # Add infinity bins for values outside training range
    bin_edges = np.concatenate([[-np.inf], bin_edges, [np.inf]])

    # Calculate expected distribution (training)
    expected_counts, _ = np.histogram(expected_clean, bins=bin_edges)
    expected_dist = expected_counts / len(expected_clean)

    # Calculate actual distribution (production)
    actual_counts, _ = np.histogram(actual_clean, bins=bin_edges)
    actual_dist = actual_counts / len(actual_clean)

    # Avoid division by zero
    expected_dist = np.where(expected_dist == 0, 0.0001, expected_dist)
    actual_dist = np.where(actual_dist == 0, 0.0001, actual_dist)

    # Calculate PSI
    psi = np.sum((actual_dist - expected_dist) * np.log(actual_dist / expected_dist))

    return float(psi)


def interpret_psi(psi_value: float) -> Tuple[str, str]:
    """
    Interpret PSI value and return status and message.

    Args:
        psi_value: Calculated PSI value

    Returns:
        Tuple of (status, message)
    """
    if psi_value < PSI_THRESHOLD_MIN:
        return "stable", f"No significant drift detected (PSI={psi_value:.4f})"
    elif psi_value < PSI_THRESHOLD_MAJOR:
        return "warning", f"Moderate drift detected (PSI={psi_value:.4f}) - investigation recommended"
    else:
        return "critical", f"Significant drift detected (PSI={psi_value:.4f}) - immediate action required"


# ============================================================================
# KOLMOGOROV-SMIRNOV (KS) TEST
# ============================================================================

def calculate_ks_test(
    expected: np.ndarray,
    actual: np.ndarray
) -> Dict[str, float]:
    """
    Perform Kolmogorov-Smirnov test for distribution difference.

    The KS test compares the empirical cumulative distribution functions
    of two samples to determine if they come from the same distribution.

    Args:
        expected: Training data distribution (reference)
        actual: Production data distribution (current)

    Returns:
        Dict with 'statistic' and 'p_value'

    Interpretation:
        - p_value >= 0.05: Distributions are similar (no drift)
        - p_value < 0.05: Distributions are different (drift detected!)
    """
    # Remove NaN values
    expected_clean = expected[~np.isnan(expected)]
    actual_clean = actual[~np.isnan(actual)]

    if len(expected_clean) == 0 or len(actual_clean) == 0:
        return {"statistic": 0.0, "p_value": 1.0}

    # Perform KS test
    statistic, p_value = stats.ks_2samp(expected_clean, actual_clean)

    return {
        "statistic": float(statistic),
        "p_value": float(p_value)
    }


def interpret_ks_test(p_value: float) -> Tuple[str, str]:
    """
    Interpret KS test p-value and return status and message.

    Args:
        p_value: P-value from KS test

    Returns:
        Tuple of (status, message)
    """
    if p_value >= KS_P_VALUE_THRESHOLD:
        return "stable", f"Distributions similar (p={p_value:.4f} >= {KS_P_VALUE_THRESHOLD})"
    else:
        return "critical", f"Distributions differ significantly (p={p_value:.4f} < {KS_P_VALUE_THRESHOLD})"


# ============================================================================
# DRIFT DETECTION - COMPREHENSIVE
# ============================================================================

def compute_drift_metrics(
    training_data: pd.DataFrame,
    production_data: pd.DataFrame,
    feature_columns: List[str]
) -> Dict[str, Any]:
    """
    Compute comprehensive drift metrics for all features.

    Calculates both PSI and KS test for each feature.

    Args:
        training_data: Reference dataset (training data)
        production_data: Current dataset (production predictions)
        feature_columns: List of feature names to check

    Returns:
        Dict with drift metrics for each feature and overall summary
    """
    logger.info(f"Computing drift metrics for {len(feature_columns)} features...")

    results = {
        "timestamp": datetime.now().isoformat(),
        "features": {},
        "summary": {
            "features_checked": len(feature_columns),
            "psi_critical": 0,
            "ks_critical": 0,
            "overall_status": "stable"
        }
    }

    for feature in feature_columns:
        if feature not in training_data.columns or feature not in production_data.columns:
            logger.warning(f"Feature '{feature}' not found in data, skipping")
            continue

        expected = training_data[feature].values
        actual = production_data[feature].values

        # Calculate PSI
        psi_value = calculate_psi(expected, actual)
        psi_status, psi_message = interpret_psi(psi_value)

        # Calculate KS test
        ks_result = calculate_ks_test(expected, actual)
        ks_status, ks_message = interpret_ks_test(ks_result["p_value"])

        # Store results
        results["features"][feature] = {
            "psi": {
                "value": psi_value,
                "status": psi_status,
                "message": psi_message
            },
            "ks_test": {
                "statistic": ks_result["statistic"],
                "p_value": ks_result["p_value"],
                "status": ks_status,
                "message": ks_message
            }
        }

        # Count critical issues
        if psi_status == "critical":
            results["summary"]["psi_critical"] += 1
        if ks_status == "critical":
            results["summary"]["ks_critical"] += 1

    # Determine overall status
    total_critical = results["summary"]["psi_critical"] + results["summary"]["ks_critical"]
    if total_critical > 0:
        results["summary"]["overall_status"] = "critical"
    elif any(results["features"][f]["psi"]["status"] == "warning" for f in results["features"]):
        results["summary"]["overall_status"] = "warning"

    logger.info(f"Drift analysis complete: {results['summary']['overall_status']} status")
    return results


# ============================================================================
# MODEL PERFORMANCE TRACKING
# ============================================================================

def compute_performance_metrics(
    predictions_log: pd.DataFrame,
    window_days: int = 7
) -> Dict[str, Any]:
    """
    Compute model performance metrics from labeled predictions.

    Requires predictions_log to have an 'actual' column for ground truth labels.

    Args:
        predictions_log: DataFrame with predictions and actual labels
        window_days: Number of days to look back for metrics

    Returns:
        Dict with performance metrics (precision, recall, f1, roc_auc)
    """
    # Filter to recent predictions with actual labels
    cutoff_date = datetime.now() - timedelta(days=window_days)
    recent_data = predictions_log[
        (predictions_log['predicted_at'] >= cutoff_date) &
        (predictions_log['actual'].notna())
    ].copy()

    if len(recent_data) == 0:
        return {
            "error": "No labeled predictions found in the specified window",
            "window_days": window_days
        }

    # Extract predictions and actuals
    y_true = recent_data['actual'].values
    y_pred = recent_data['prediction'].values

    # Basic metrics
    tp = ((y_true == 1) & (y_pred == 1)).sum()
    tn = ((y_true == 0) & (y_pred == 0)).sum()
    fp = ((y_true == 0) & (y_pred == 1)).sum()
    fn = ((y_true == 1) & (y_pred == 0)).sum()

    # Calculate metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Calculate ROC-AUC if we have probabilities
    roc_auc = None
    if 'confidence' in recent_data.columns:
        try:
            from sklearn.metrics import roc_auc_score
            roc_auc = roc_auc_score(y_true, recent_data['confidence'].values)
        except Exception as e:
            logger.warning(f"Could not calculate ROC-AUC: {e}")

    return {
        "window_days": window_days,
        "sample_size": len(recent_data),
        "confusion_matrix": {"tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)},
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "roc_auc": float(roc_auc) if roc_auc else None,
        "kpi_status": {
            "precision_pass": precision >= PRECISION_THRESHOLD,
            "recall_pass": recall >= RECALL_THRESHOLD
        }
    }


def check_performance_degradation(
    current_metrics: Dict[str, Any],
    baseline_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Check if model performance has degraded beyond acceptable thresholds.

    Args:
        current_metrics: Current performance metrics
        baseline_metrics: Baseline metrics for comparison (optional)

    Returns:
        Dict with degradation status and alerts
    """
    alerts = []

    # Check precision
    precision = current_metrics.get("precision", 0)
    if precision < PRECISION_THRESHOLD:
        alerts.append({
            "metric": "precision",
            "severity": "critical" if precision < PRECISION_THRESHOLD * 0.9 else "warning",
            "current": precision,
            "threshold": PRECISION_THRESHOLD,
            "message": f"Precision ({precision:.4f}) below threshold ({PRECISION_THRESHOLD:.2f})"
        })

    # Check recall
    recall = current_metrics.get("recall", 0)
    if recall < RECALL_THRESHOLD:
        alerts.append({
            "metric": "recall",
            "severity": "critical" if recall < RECALL_THRESHOLD * 0.9 else "warning",
            "current": recall,
            "threshold": RECALL_THRESHOLD,
            "message": f"Recall ({recall:.4f}) below threshold ({RECALL_THRESHOLD:.2f})"
        })

    # Compare with baseline if provided
    if baseline_metrics:
        baseline_precision = baseline_metrics.get("precision", precision)
        baseline_recall = baseline_metrics.get("recall", recall)

        # Check for significant drop (>10% relative)
        if precision < baseline_precision * 0.9:
            alerts.append({
                "metric": "precision",
                "severity": "warning",
                "current": precision,
                "baseline": baseline_precision,
                "message": f"Precision dropped {(1 - precision/baseline_precision)*100:.1f}% from baseline"
            })

        if recall < baseline_recall * 0.9:
            alerts.append({
                "metric": "recall",
                "severity": "warning",
                "current": recall,
                "baseline": baseline_recall,
                "message": f"Recall dropped {(1 - recall/baseline_recall)*100:.1f}% from baseline"
            })

    return {
        "has_degradation": len(alerts) > 0,
        "alerts": alerts,
        "overall_status": "critical" if any(a.get("severity") == "critical" for a in alerts) else "warning" if alerts else "healthy"
    }


# ============================================================================
# ALERTING SYSTEM
# ============================================================================

class AlertManager:
    """
    Manages alert generation and delivery.

    Supports email notifications and alert logging.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize AlertManager.

        Args:
            config: Configuration dict with email settings
        """
        self.config = config or self._load_default_config()
        self.alert_log = ALERT_LOG_FILE
        self.alert_log.parent.mkdir(exist_ok=True)

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration from environment variables."""
        return {
            "email": {
                "enabled": os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true",
                "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "sender_email": os.getenv("ALERT_SENDER_EMAIL", ""),
                "sender_password": os.getenv("ALERT_SENDER_PASSWORD", ""),
                "recipients": os.getenv("ALERT_RECIPIENTS", "").split(",") if os.getenv("ALERT_RECIPIENTS") else [],
            },
            "thresholds": {
                "psi_critical": PSI_THRESHOLD_MAJOR,
                "ks_p_value": KS_P_VALUE_THRESHOLD,
                "recall_min": RECALL_THRESHOLD,
                "precision_min": PRECISION_THRESHOLD,
            }
        }

    def log_alert(self, alert_data: Dict[str, Any]) -> None:
        """
        Log alert to file for audit trail.

        Args:
            alert_data: Alert information dictionary
        """
        alert_entry = {
            "timestamp": datetime.now().isoformat(),
            **alert_data
        }

        with open(self.alert_log, 'a') as f:
            f.write(str(alert_entry).replace("'", '"') + '\n')

        logger.info(f"Alert logged: {alert_data.get('type', 'Unknown')}")

    def send_email_alert(
        self,
        subject: str,
        body: str,
        severity: str = "info"
    ) -> bool:
        """
        Send email notification.

        Args:
            subject: Email subject line
            body: Email body content
            severity: Alert severity (info, warning, critical)

        Returns:
            bool: True if email was sent successfully
        """
        if not self.config["email"]["enabled"]:
            logger.info("Email alerts disabled, skipping send")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{severity.upper()}] {subject}"
            msg['From'] = self.config["email"]["sender_email"]
            msg['To'] = ", ".join(self.config["email"]["recipients"])

            # Add body
            msg.attach(MIMEText(body, 'plain'))

            # Send email
            with smtplib.SMTP(
                self.config["email"]["smtp_server"],
                self.config["email"]["smtp_port"]
            ) as server:
                server.starttls()
                server.login(
                    self.config["email"]["sender_email"],
                    self.config["email"]["sender_password"]
                )
                server.send_message(msg)

            logger.info(f"Email alert sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def create_drift_alert(
        self,
        drift_metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create alert from drift metrics if thresholds exceeded.

        Args:
            drift_metrics: Drift analysis results

        Returns:
            Alert dict if alert triggered, None otherwise
        """
        if drift_metrics["summary"]["overall_status"] == "stable":
            return None

        # Identify critical features
        critical_features = []
        for feature, data in drift_metrics["features"].items():
            if data["psi"]["status"] == "critical" or data["ks_test"]["status"] == "critical":
                critical_features.append(feature)

        # Create alert
        alert = {
            "type": "data_drift",
            "severity": drift_metrics["summary"]["overall_status"],
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "critical_features": critical_features,
                "psi_critical_count": drift_metrics["summary"]["psi_critical"],
                "ks_critical_count": drift_metrics["summary"]["ks_critical"],
            },
            "details": drift_metrics
        }

        # Send email alert
        subject = f"Data Drift Detected - {len(critical_features)} Features Affected"
        body = f"""
Data drift has been detected in the fraud detection model.

Summary:
- Features with critical drift: {len(critical_features)}
- PSI critical count: {drift_metrics['summary']['psi_critical']}
- KS test critical count: {drift_metrics['summary']['ks_critical']}

Critical features: {', '.join(critical_features[:10])}
{'...' if len(critical_features) > 10 else ''}

Recommendation: Investigate feature distributions and consider retraining.
Timestamp: {datetime.now().isoformat()}
"""

        self.send_email_alert(subject, body, alert["severity"])
        self.log_alert(alert)

        return alert

    def create_performance_alert(
        self,
        performance_check: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create alert from performance degradation check.

        Args:
            performance_check: Performance degradation results

        Returns:
            Alert dict if alert triggered, None otherwise
        """
        if not performance_check["has_degradation"]:
            return None

        # Create alert
        alert = {
            "type": "performance_degradation",
            "severity": performance_check["overall_status"],
            "timestamp": datetime.now().isoformat(),
            "alerts": performance_check["alerts"]
        }

        # Send email alert
        critical_alerts = [a for a in performance_check["alerts"] if a["severity"] == "critical"]
        subject = f"Model Performance Degradation - {len(performance_check['alerts'])} Alerts"

        body_lines = ["Model performance has degraded below acceptable thresholds.\n"]
        for alert_data in performance_check["alerts"]:
            body_lines.append(f"- {alert_data['metric'].upper()}: {alert_data['message']}")

        body_lines.append(f"\nTimestamp: {datetime.now().isoformat()}")
        body_lines.append("\nRecommendation: Consider retraining the model with recent data.")

        body = "\n".join(body_lines)

        self.send_email_alert(subject, body, alert["severity"])
        self.log_alert(alert)

        return alert


# ============================================================================
# RETRAINING TRIGGERS
# ============================================================================

def should_trigger_retraining(
    drift_metrics: Dict[str, Any],
    performance_check: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Determine if model retraining should be triggered.

    Triggers retraining if:
    1. Data drift is critical (PSI >= 0.2 for multiple features)
    2. Performance has degraded significantly
    3. Scheduled retraining (time-based) - not implemented yet

    Args:
        drift_metrics: Drift analysis results
        performance_check: Optional performance degradation check

    Returns:
        Tuple of (should_retrain: bool, reason: str)
    """
    reasons = []

    # Check data drift
    if drift_metrics["summary"]["overall_status"] == "critical":
        critical_count = (
            drift_metrics["summary"]["psi_critical"] +
            drift_metrics["summary"]["ks_critical"]
        )
        if critical_count >= 3:
            reasons.append(f"Significant data drift in {critical_count} features")

    # Check performance degradation
    if performance_check and performance_check.get("has_degradation"):
        if performance_check["overall_status"] == "critical":
            reasons.append("Critical performance degradation detected")

    should_retrain = len(reasons) > 0
    reason = "; ".join(reasons) if reasons else "No retraining trigger"

    return should_retrain, reason


def trigger_retraining(triggered_by: str = "drift", force_promote: bool = False) -> Dict[str, Any]:
    """
    Trigger automated model retraining pipeline.

    Calls the complete retraining pipeline implemented in src/retraining.py
    per project_guide.md Week 4 Day 4.

    Pipeline:
    1. Pull latest data from database
    2. Train new model with current hyperparameters
    3. Validate new model meets performance criteria
    4. Deploy new model (zero-downtime)
    5. Notify team of deployment

    Args:
        triggered_by: What triggered the retraining ('drift', 'scheduled', 'manual')
        force_promote: Skip validation and promote regardless

    Returns:
        Dict with retraining status
    """
    logger.info(f"Retraining triggered by: {triggered_by}")

    try:
        from src.retraining import run_retraining_pipeline

        result = run_retraining_pipeline(
            triggered_by=triggered_by,
            data_window_days=30,
            force_promote=force_promote
        )

        return result

    except ImportError as e:
        logger.error(f"Failed to import retraining module: {e}")
        return {
            "status": "failed",
            "error": f"Retraining module not available: {e}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Retraining pipeline failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# MONITORING ORCHESTRATION
# ============================================================================

def run_monitoring_checks(
    training_data_path: str,
    production_data_path: Optional[str] = None,
    model_path: str = None
) -> Dict[str, Any]:
    """
    Run all monitoring checks and generate comprehensive report.

    This is the main entry point for the monitoring system.

    Args:
        training_data_path: Path to training data reference
        production_data_path: Path to production data (or None to load from DB)
        model_path: Path to trained model

    Returns:
        Comprehensive monitoring report
    """
    logger.info("Starting monitoring checks...")

    # Load training data reference
    try:
        training_data = joblib.load(training_data_path)
        if isinstance(training_data, dict):
            # Handle saved training data dict
            training_data = pd.DataFrame(training_data)
    except Exception as e:
        logger.error(f"Failed to load training data: {e}")
        return {"error": f"Cannot load training data: {e}"}

    # Load production data (from database or file)
    try:
        if production_data_path:
            production_data = joblib.load(production_data_path)
        else:
            # Load from database (PostgreSQL)
            import psycopg2
            import os
            from dotenv import load_dotenv
            load_dotenv()

            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 5432)),
                database=os.getenv("DB_NAME", "fraud_detection"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "")
            )

            query = """
                SELECT v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
                       v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
                       v21, v22, v23, v24, v25, v26, v27, v28
                FROM predictions_log
                ORDER BY predicted_at DESC
                LIMIT 10000
            """

            production_data = pd.read_sql_query(query, conn)
            conn.close()

    except Exception as e:
        logger.error(f"Failed to load production data: {e}")
        return {"error": f"Cannot load production data: {e}"}

    # Feature columns to check
    feature_columns = [f"v{i}" for i in range(1, 29)]

    # Run drift detection
    drift_metrics = compute_drift_metrics(
        training_data=training_data,
        production_data=production_data,
        feature_columns=feature_columns
    )

    # Initialize alert manager
    alert_manager = AlertManager()

    # Create drift alert if needed
    drift_alert = alert_manager.create_drift_alert(drift_metrics)

    # Compile report
    report = {
        "timestamp": datetime.now().isoformat(),
        "drift_analysis": drift_metrics,
        "drift_alert": drift_alert,
        "recommendations": []
    }

    # Add recommendations
    if drift_metrics["summary"]["overall_status"] != "stable":
        report["recommendations"].append("Investigate drifted features and consider retraining")
        report["recommendations"].append("Review data pipeline for data quality issues")

    # Check if retraining should be triggered
    should_retrain, retrain_reason = should_trigger_retraining(drift_metrics)
    report["retraining"] = {
        "triggered": should_retrain,
        "reason": retrain_reason
    }

    if should_retrain:
        logger.warning(f"Retraining triggered: {retrain_reason}")

    logger.info("Monitoring checks complete")
    return report


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Run monitoring checks as standalone script.

    Usage:
        python src/monitoring.py
    """
    print("="*70)
    print("     FRAUD DETECTION - MONITORING SYSTEM")
    print("="*70)

    # Example usage with saved training data
    training_data_path = "data/processed/X_train.pkl"

    if Path(training_data_path).exists():
        report = run_monitoring_checks(training_data_path=training_data_path)

        print("\nMonitoring Report:")
        print(f"  Overall Status: {report['drift_analysis']['summary']['overall_status']}")
        print(f"  Features Checked: {report['drift_analysis']['summary']['features_checked']}")
        print(f"  Critical Drifts: {report['drift_analysis']['summary']['psi_critical']} (PSI), {report['drift_analysis']['summary']['ks_critical']} (KS)")

        if report.get("recommendations"):
            print("\nRecommendations:")
            for rec in report["recommendations"]:
                print(f"  - {rec}")
    else:
        print(f"Error: Training data not found at {training_data_path}")
        print("Please ensure model training has been completed and data is saved.")
