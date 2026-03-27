"""
Alert Scheduler - Runs monitoring checks periodically

Usage:
    python src/alert_scheduler.py

Or run as a cron job:
    */5 * * * * cd /path/to/project && python src/alert_scheduler.py >> logs/alert_scheduler.log 2>&1

This will run monitoring checks every 5 minutes.
"""
import time
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.alerting import run_monitoring_checks, logger

# Configure logging for scheduler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - ALERT_SCHEDULER - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "logs" / "alert_scheduler.log"),
        logging.StreamHandler()
    ]
)


def main():
    """Run monitoring checks once (designed for cron scheduling)."""
    logger.info("=" * 60)
    logger.info("ALERT SCHEDULER: Running monitoring checks")
    logger.info("=" * 60)

    try:
        results = run_monitoring_checks()

        # Log summary
        alert_count = results["summary"]["alerts_triggered"]
        if alert_count > 0:
            logger.warning(f"⚠️ {alert_count} alert(s) triggered!")
            for alert in results["alerts_triggered"]:
                logger.warning(f"  - {alert['type']}: {alert['severity']}")
        else:
            logger.info("✓ All checks passed - no alerts")

        return 0

    except Exception as e:
        logger.error(f"Monitoring run failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
