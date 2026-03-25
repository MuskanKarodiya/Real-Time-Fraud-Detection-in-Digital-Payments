"""
Dashboard Data API Module

Provides data access functions for FastAPI dashboard endpoints.
Similar to dashboard/utils/data_loader.py but without Streamlit dependencies.

This module is used by app/main.py for /api/v1/dashboard/* endpoints.
"""
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

from app.config import DB_CONFIG

# Database connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


def get_db_connection():
    """Get a connection to PostgreSQL database."""
    if not DB_AVAILABLE:
        raise RuntimeError("psycopg2 not installed")

    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        connect_timeout=5
    )


def get_stats() -> Dict[str, Any]:
    """Get summary statistics from predictions database."""
    try:
        conn = get_db_connection()

        query = """
            SELECT
                COUNT(*) as total_count,
                SUM(prediction) as fraud_count,
                AVG(confidence) as avg_fraud_probability,
                AVG(latency_ms) as avg_response_time_ms
            FROM predictions_log
        """

        df = pd.read_sql_query(query, conn)

        # Get risk level breakdown
        risk_query = """
            SELECT risk_level, COUNT(*) as count
            FROM predictions_log
            GROUP BY risk_level
        """
        risk_df = pd.read_sql_query(risk_query, conn)
        conn.close()

        if df.empty or df['total_count'].iloc[0] == 0:
            return {
                'total_count': 0,
                'fraud_count': 0,
                'fraud_rate': 0.0,
                'avg_fraud_probability': 0.0,
                'avg_response_time_ms': 0.0,
                'risk_counts': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
            }

        total = int(df['total_count'].iloc[0])
        fraud = int(df['fraud_count'].iloc[0])
        fraud_rate = (fraud / total * 100) if total > 0 else 0.0
        avg_prob = float(df['avg_fraud_probability'].iloc[0]) if pd.notna(df['avg_fraud_probability'].iloc[0]) else 0.0
        avg_rt = float(df['avg_response_time_ms'].iloc[0]) if pd.notna(df['avg_response_time_ms'].iloc[0]) else 0.0

        risk_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for _, row in risk_df.iterrows():
            risk_counts[row['risk_level']] = int(row['count'])

        return {
            'total_count': total,
            'fraud_count': fraud,
            'fraud_rate': round(fraud_rate, 2),
            'avg_fraud_probability': round(avg_prob, 4),
            'avg_response_time_ms': round(avg_rt, 2),
            'risk_counts': risk_counts,
        }

    except Exception as e:
        return {
            'total_count': 0,
            'fraud_count': 0,
            'fraud_rate': 0.0,
            'avg_fraud_probability': 0.0,
            'avg_response_time_ms': 0.0,
            'risk_counts': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
        }


def get_hourly_stats(hours: int = 24) -> Dict[str, Any]:
    """Get hourly transaction and fraud rate stats from database."""
    try:
        conn = get_db_connection()

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = """
            SELECT
                DATE_TRUNC('hour', predicted_at) as hour,
                COUNT(*) as count,
                SUM(prediction)::int as fraud_count
            FROM predictions_log
            WHERE predicted_at >= %s
            GROUP BY DATE_TRUNC('hour', predicted_at)
            ORDER BY hour
        """

        df = pd.read_sql_query(query, conn, params=(cutoff,))
        conn.close()

        if df.empty:
            return {'labels': [], 'volumes': [], 'fraud_rates': []}

        df['hour'] = pd.to_datetime(df['hour'], utc=True)
        df['fraud_rate'] = (df['fraud_count'] / df['count'] * 100).round(2)

        return {
            'labels': df['hour'].dt.strftime('%H:00').tolist(),
            'volumes': df['count'].astype(int).tolist(),
            'fraud_rates': df['fraud_rate'].tolist(),
        }

    except Exception as e:
        return {'labels': [], 'volumes': [], 'fraud_rates': []}


def get_response_times(limit: int = 100) -> List[float]:
    """Get recent response times from database."""
    try:
        conn = get_db_connection()

        query = """
            SELECT latency_ms
            FROM predictions_log
            WHERE latency_ms IS NOT NULL
            ORDER BY predicted_at DESC
            LIMIT %s
        """

        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()

        if df.empty:
            return []

        # Return in chronological order (oldest first)
        return df['latency_ms'].iloc[::-1].tolist()

    except Exception as e:
        return []


def get_high_risk_transactions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get high-risk transactions from database."""
    try:
        conn = get_db_connection()

        query = """
            SELECT
                transaction_id,
                confidence as fraud_probability,
                prediction,
                risk_level,
                latency_ms as response_time_ms,
                predicted_at as timestamp
            FROM predictions_log
            WHERE risk_level = 'HIGH'
            ORDER BY predicted_at DESC
            LIMIT %s
        """

        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()

        if df.empty:
            return []

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        return df.to_dict('records')

    except Exception as e:
        return []


def get_probability_distribution() -> Dict[str, Any]:
    """
    Get fraud probability distribution from model test set evaluation.

    Based on test set performance (n=56,962) from model training.
    """
    bins = [
        '0.0-0.1', '0.1-0.2', '0.2-0.3', '0.3-0.4', '0.4-0.5',
        '0.5-0.6', '0.6-0.7', '0.7-0.8', '0.8-0.9', '0.9-1.0'
    ]
    counts = [56820, 18, 8, 4, 3, 5, 8, 12, 25, 59]

    return {
        'bins': bins,
        'counts': counts,
    }


def get_recent_predictions(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent predictions from database."""
    try:
        conn = get_db_connection()

        query = """
            SELECT
                transaction_id,
                prediction,
                confidence as fraud_probability,
                risk_level,
                latency_ms as response_time_ms,
                predicted_at as timestamp
            FROM predictions_log
            ORDER BY predicted_at DESC
            LIMIT %s
        """

        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()

        if df.empty:
            return []

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        return df.to_dict('records')

    except Exception as e:
        return []


def get_errors(limit: int = 20) -> List[Dict[str, Any]]:
    """Load errors from database."""
    try:
        conn = get_db_connection()

        # Check if error_logs table exists
        check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'error_logs'
            )
        """

        cur = conn.cursor()
        cur.execute(check_query)
        table_exists = cur.fetchone()[0]

        if not table_exists:
            cur.close()
            conn.close()
            return []

        query = """
            SELECT
                endpoint,
                error_type,
                error_message,
                transaction_id,
                amount,
                predicted_at as timestamp
            FROM error_logs
            ORDER BY predicted_at DESC
            LIMIT %s
        """

        cur.execute(query, (limit,))
        columns = [desc[0] for desc in cur.description]
        errors = [dict(zip(columns, row)) for row in cur.fetchall()]

        cur.close()
        conn.close()

        return errors

    except Exception as e:
        return []
