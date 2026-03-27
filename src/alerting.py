"""
Alerting System - Week 4 Day 3-4

Monitors system health and sends email alerts via Gmail.

Alerts (per project_guide.md):
- API Error Rate: > 1% in 5-minute window
- Latency Spike: p99 > 500ms sustained for 10 minutes
- Model Degradation: Precision/recall drops > 5% from baseline
- Pipeline Failure: ETL or retraining job fails

Environment Variables Required:
    ALERT_EMAIL_ENABLED: true/false
    ALERT_SENDER_EMAIL: Gmail address for sending alerts
    ALERT_SENDER_PASSWORD: Gmail App-Specific Password
    ALERT_RECIPIENTS: Comma-separated list of recipient emails
"""
import os
import smtplib
import json
import logging
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "fraud_detection"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Alert thresholds (per project_guide.md)
ALERT_THRESHOLDS = {
    "api_error_rate_percent": 1.0,      # > 1% error rate
    "api_error_window_minutes": 5,       # Rolling 5-minute window
    "latency_p99_ms": 500,               # p99 > 500ms
    "latency_window_minutes": 10,        # Sustained for 10 minutes
    "latency_min_samples": 10,           # Minimum samples required
    "model_degradation_percent": 5.0,    # > 5% drop from baseline
}


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection using psycopg2."""
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
        return conn
    except ImportError:
        logger.error("psycopg2 not installed")
        raise
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


# ============================================================================
# EMAIL SENDING (GMAIL SMTP)
# ============================================================================

class EmailAlerter:
    """Sends email alerts via Gmail SMTP."""

    def __init__(self):
        """Initialize email alerter from environment variables."""
        self.enabled = os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("ALERT_SENDER_EMAIL", "")
        self.sender_password = os.getenv("ALERT_SENDER_PASSWORD", "")
        self.recipients = os.getenv("ALERT_RECIPIENTS", "").split(",") if os.getenv("ALERT_RECIPIENTS") else []

        if self.enabled and not self.sender_email:
            logger.warning("ALERT_EMAIL_ENABLED=true but ALERT_SENDER_EMAIL not set")
            self.enabled = False

        if self.enabled and not self.sender_password:
            logger.warning("ALERT_SENDER_PASSWORD not set")
            self.enabled = False

        if self.enabled and not self.recipients:
            logger.warning("ALERT_RECIPIENTS not set")
            self.enabled = False

    def send_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send alert email.

        Args:
            alert_type: Type of alert (api_error_rate, latency_spike, etc.)
            severity: Severity level (info, warning, critical)
            title: Alert title
            message: Alert message
            details: Additional details (will be JSON-encoded)

        Returns:
            bool: True if email sent successfully
        """
        if not self.enabled:
            logger.info(f"Email alerts disabled. Would send: {title}")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{severity.upper()}] Fraud Detection Alert: {title}"
            msg['From'] = self.sender_email
            msg['To'] = ", ".join(self.recipients)

            # Build email body
            body_parts = [
                f"Alert Type: {alert_type}",
                f"Severity: {severity.upper()}",
                f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
                "",
                message,
                ""
            ]

            if details:
                body_parts.append("Details:")
                for key, value in details.items():
                    body_parts.append(f"  {key}: {value}")

            body = "\n".join(body_parts)

            msg.attach(MIMEText(body, 'plain'))

            # Send via Gmail SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"Alert email sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


# ============================================================================
# ALERT LOGGING TO DATABASE
# ============================================================================

def log_alert_to_db(
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    email_sent: bool = False
) -> bool:
    """
    Log alert to PostgreSQL alerts_log table.

    Args:
        alert_type: Type of alert
        severity: Severity level
        title: Alert title
        message: Alert message
        details: Additional details (JSONB)
        email_sent: Whether email was sent

    Returns:
        bool: True if logged successfully
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Convert details to JSON for PostgreSQL
        details_json = json.dumps(details) if details else None

        query = """
            INSERT INTO alerts_log (alert_type, severity, title, message, details, email_sent)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            alert_type,
            severity,
            title[:200],  # Limit to varchar(200)
            message,
            details_json,
            email_sent
        ))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Alert logged to DB: {title}")
        return True

    except Exception as e:
        logger.error(f"Failed to log alert to DB: {e}")
        return False


# ============================================================================
# ALERT CHECK FUNCTIONS
# ============================================================================

def check_api_error_rate(alerter: EmailAlerter) -> Optional[Dict[str, Any]]:
    """
    Check API error rate in last 5 minutes.

    Alert if error rate > 1%

    Returns:
        Alert dict if triggered, None otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Count total requests and errors in last 5 minutes
        window_minutes = ALERT_THRESHOLDS["api_error_window_minutes"]
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        # Get total requests from predictions_log
        query = """
            SELECT COUNT(*) as total_requests
            FROM predictions_log
            WHERE predicted_at >= %s
        """

        cursor.execute(query, (cutoff,))
        result = cursor.fetchone()
        total_requests = result[0] if result else 0

        # Get error count from error_logs
        error_query = """
            SELECT COUNT(*) as error_count
            FROM error_logs
            WHERE predicted_at >= %s
        """

        cursor.execute(error_query, (cutoff,))
        error_result = cursor.fetchone()
        error_count = error_result[0] if error_result else 0

        cursor.close()
        conn.close()

        if total_requests < 10:  # Minimum threshold for meaningful rate
            return None

        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        threshold = ALERT_THRESHOLDS["api_error_rate_percent"]

        if error_rate > threshold:
            severity = "critical" if error_rate > 5 else "warning"
            title = f"API Error Rate High: {error_rate:.2f}%"
            message = (
                f"API error rate is {error_rate:.2f}%, exceeding threshold of {threshold}%.\n"
                f"Errors: {error_count} out of {total_requests} requests in last {window_minutes} minutes."
            )

            details = {
                "error_rate_percent": round(error_rate, 2),
                "threshold_percent": threshold,
                "error_count": error_count,
                "total_requests": total_requests,
                "window_minutes": window_minutes
            }

            # Send email and log to DB
            email_sent = alerter.send_alert("api_error_rate", severity, title, message, details)
            log_alert_to_db("api_error_rate", severity, title, message, details, email_sent)

            return {
                "type": "api_error_rate",
                "severity": severity,
                "triggered": True,
                "details": details
            }

        return None

    except Exception as e:
        logger.error(f"Error checking API error rate: {e}")
        return None


def check_latency_spike(alerter: EmailAlerter) -> Optional[Dict[str, Any]]:
    """
    Check for latency spikes (p99 > 500ms sustained).

    Alert if p99 latency > 500ms for sustained period.

    Returns:
        Alert dict if triggered, None otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        window_minutes = ALERT_THRESHOLDS["latency_window_minutes"]
        min_samples = ALERT_THRESHOLDS["latency_min_samples"]
        threshold_ms = ALERT_THRESHOLDS["latency_p99_ms"]

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        query = """
            SELECT
                COUNT(*) as sample_count,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency,
                AVG(latency_ms) as avg_latency,
                MAX(latency_ms) as max_latency
            FROM predictions_log
            WHERE predicted_at >= %s
            AND latency_ms IS NOT NULL
        """

        cursor.execute(query, (cutoff,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result or result[0] < min_samples:
            return None

        sample_count = int(result[0])
        p99_latency = float(result[1]) if result[1] else 0
        avg_latency = float(result[2]) if result[2] else 0
        max_latency = float(result[3]) if result[3] else 0

        if p99_latency > threshold_ms:
            severity = "critical" if p99_latency > 1000 else "warning"
            title = f"Latency Spike Detected: p99 = {p99_latency:.0f}ms"
            message = (
                f"API latency has spiked above threshold.\n"
                f"p99 latency: {p99_latency:.0f}ms (threshold: {threshold_ms}ms)\n"
                f"Average: {avg_latency:.0f}ms, Max: {max_latency:.0f}ms\n"
                f"Based on {sample_count} requests in last {window_minutes} minutes."
            )

            details = {
                "p99_latency_ms": round(p99_latency, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "max_latency_ms": round(max_latency, 2),
                "threshold_ms": threshold_ms,
                "sample_count": sample_count,
                "window_minutes": window_minutes
            }

            # Send email and log to DB
            email_sent = alerter.send_alert("latency_spike", severity, title, message, details)
            log_alert_to_db("latency_spike", severity, title, message, details, email_sent)

            return {
                "type": "latency_spike",
                "severity": severity,
                "triggered": True,
                "details": details
            }

        return None

    except Exception as e:
        logger.error(f"Error checking latency spike: {e}")
        return None


def check_model_degradation(alerter: EmailAlerter) -> Optional[Dict[str, Any]]:
    """
    Check for model performance degradation.

    Compares recent metrics against baseline from model training.

    Returns:
        Alert dict if triggered, None otherwise
    """
    try:
        # Load baseline from model metadata
        metadata_path = Path("models/metadata.json")
        if not metadata_path.exists():
            return None

        with open(metadata_path) as f:
            metadata = json.load(f)

        baseline_metrics = metadata.get("metrics", {})
        baseline_precision = baseline_metrics.get("precision", 0.8646)
        baseline_recall = baseline_metrics.get("recall", 0.8469)

        degradation_threshold = ALERT_THRESHOLDS["model_degradation_percent"] / 100  # 5%

        # For now, we can't compute actual current metrics without ground truth labels
        # This is a placeholder that checks if the model file is recent
        model_path = Path("models/fraud_detector_v1.pkl")
        if not model_path.exists():
            return None

        model_age_days = (datetime.now() - datetime.fromtimestamp(model_path.stat().st_mtime)).days

        # Alert if model is older than 30 days (signaling potential degradation)
        if model_age_days > 30:
            severity = "warning" if model_age_days < 60 else "critical"
            title = f"Model Age Warning: {model_age_days} days old"
            message = (
                f"Model has not been retrained in {model_age_days} days.\n"
                f"Baseline metrics - Precision: {baseline_precision:.4f}, Recall: {baseline_recall:.4f}\n"
                f"Consider retraining with recent data to maintain performance."
            )

            details = {
                "model_age_days": model_age_days,
                "baseline_precision": baseline_precision,
                "baseline_recall": baseline_recall,
                "last_training": metadata.get("training_date", "Unknown")
            }

            # Send email and log to DB
            email_sent = alerter.send_alert("model_degradation", severity, title, message, details)
            log_alert_to_db("model_degradation", severity, title, message, details, email_sent)

            return {
                "type": "model_degradation",
                "severity": severity,
                "triggered": True,
                "details": details
            }

        return None

    except Exception as e:
        logger.error(f"Error checking model degradation: {e}")
        return None


# ============================================================================
# MAIN MONITORING RUN
# ============================================================================

def run_monitoring_checks() -> Dict[str, Any]:
    """
    Run all monitoring checks and send alerts if thresholds exceeded.

    Returns:
        Summary of monitoring run
    """
    logger.info("Starting monitoring checks...")

    # Initialize email alerter
    alerter = EmailAlerter()

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "alerts_triggered": []
    }

    # Check API error rate
    logger.info("Checking API error rate...")
    api_error_result = check_api_error_rate(alerter)
    results["checks"]["api_error_rate"] = {
        "triggered": api_error_result is not None,
        "details": api_error_result.get("details") if api_error_result else None
    }
    if api_error_result:
        results["alerts_triggered"].append(api_error_result)

    # Check latency spike
    logger.info("Checking latency spikes...")
    latency_result = check_latency_spike(alerter)
    results["checks"]["latency_spike"] = {
        "triggered": latency_result is not None,
        "details": latency_result.get("details") if latency_result else None
    }
    if latency_result:
        results["alerts_triggered"].append(latency_result)

    # Check model degradation
    logger.info("Checking model degradation...")
    model_result = check_model_degradation(alerter)
    results["checks"]["model_degradation"] = {
        "triggered": model_result is not None,
        "details": model_result.get("details") if model_result else None
    }
    if model_result:
        results["alerts_triggered"].append(model_result)

    results["summary"] = {
        "total_checks": len(results["checks"]),
        "alerts_triggered": len(results["alerts_triggered"]),
        "status": "alert" if len(results["alerts_triggered"]) > 0 else "healthy"
    }

    logger.info(f"Monitoring complete: {len(results['alerts_triggered'])} alerts triggered")
    return results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("     FRAUD DETECTION - ALERTING SYSTEM")
    print("=" * 70)
    print()

    # Check configuration
    alerter = EmailAlerter()
    print(f"Email Alerts Enabled: {alerter.enabled}")
    if alerter.enabled:
        print(f"Sender: {alerter.sender_email}")
        print(f"Recipients: {alerter.recipients}")
    print()

    # Run checks
    results = run_monitoring_checks()

    # Print summary
    print("-" * 70)
    print("MONITORING SUMMARY")
    print("-" * 70)
    print(f"Status: {results['summary']['status'].upper()}")
    print(f"Checks Run: {results['summary']['total_checks']}")
    print(f"Alerts Triggered: {results['summary']['alerts_triggered']}")

    for check_name, check_result in results["checks"].items():
        status_icon = "[!]" if check_result["triggered"] else "[OK]"
        print(f"  {status_icon} {check_name}: {'TRIGGERED' if check_result['triggered'] else 'OK'}")

    print()
    print(f"Timestamp: {results['timestamp']}")
