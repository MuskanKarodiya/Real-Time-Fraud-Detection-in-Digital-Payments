"""
Page 5: Drift Monitor

Monitor data drift, model performance degradation, and automated alerts.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import numpy as np
import json

from dashboard.config import (
    SUCCESS,
    DANGER,
    WARNING,
    PRIMARY,
    inject_shared_styles,
    build_sidebar,
)
from dashboard.utils.charts import (
    create_psi_heatmap,
    create_ks_test_chart,
    create_drift_summary_card,
    create_feature_drift_table,
)
from dashboard.utils.data_loader import check_db_connection

# Try importing monitoring module
try:
    from src.monitoring import (
        compute_drift_metrics,
        calculate_psi,
        calculate_ks_test,
        PSI_THRESHOLD_MIN,
        PSI_THRESHOLD_MAJOR,
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════
# SHARED STYLES (must be first)
# ═══════════════════════════════════════════════════════════════════════

inject_shared_styles()

# Build sidebar
build_sidebar(current_page="Drift Monitor")


# ═══════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; margin-top: 20px;">
    <div>
        <div style="font-size: 20px; font-weight: 700; color: #333333;">📊 Drift Monitor</div>
        <div style="font-size: 11px; color: #757575; margin-top: 2px;">Data drift detection · PSI & KS-test · Model performance tracking</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=30)
def load_drift_data():
    """Load training data reference and production data for drift analysis.

    Training reference: Sample from transactions_raw (first 10K rows)
    Production data: From prediction_inputs (recent 5K predictions with features)

    Uses database directly to avoid pickle compatibility issues with X_train.pkl
    """
    try:
        import psycopg2
        import os
        from dotenv import load_dotenv
        load_dotenv()

        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME", "fraud_detection"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            connect_timeout=5
        )

        # Load training reference: First 10K rows from transactions_raw
        # This represents the original training distribution
        train_query = """
            SELECT v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
                   v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
                   v21, v22, v23, v24, v25, v26, v27, v28
            FROM transactions_raw
            ORDER BY id
            LIMIT 10000
        """

        X_train = pd.read_sql_query(train_query, conn)

        # Load production data from prediction_inputs (contains V1-V28 features)
        prod_query = """
            SELECT v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
                   v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
                   v21, v22, v23, v24, v25, v26, v27, v28
            FROM prediction_inputs
            ORDER BY predicted_at DESC
            LIMIT 5000
        """

        X_prod = pd.read_sql_query(prod_query, conn)
        conn.close()

        if X_train.empty:
            return None, "No training data available in transactions_raw table"

        if X_prod.empty:
            return (X_train, pd.DataFrame()), None  # Return empty production data

        return (X_train, X_prod), None

    except Exception as e:
        return None, f"Failed to load data from database: {e}"


@st.cache_data(ttl=30)
def compute_drift_analysis():
    """Compute drift metrics from training and production data."""
    result, error = load_drift_data()

    if error:
        return None, error

    X_train, X_prod = result

    # Check if production data is empty
    if X_prod.empty:
        return None, "No production data available in prediction_inputs. Make some live predictions first to populate drift monitoring data."

    # Feature columns to check (V1-V28)
    feature_columns = [f"v{i}" for i in range(1, 29)]

    # Compute drift metrics
    drift_metrics = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "features": {},
        "summary": {
            "features_checked": len(feature_columns),
            "psi_critical": 0,
            "ks_critical": 0,
            "overall_status": "stable"
        }
    }

    for feature in feature_columns:
        if feature not in X_train.columns or feature not in X_prod.columns:
            continue

        expected = X_train[feature].values
        actual = X_prod[feature].values

        # Calculate PSI
        psi_value = calculate_psi(expected, actual)
        if psi_value < PSI_THRESHOLD_MIN:
            psi_status = "stable"
        elif psi_value < PSI_THRESHOLD_MAJOR:
            psi_status = "warning"
        else:
            psi_status = "critical"

        # Calculate KS test
        ks_result = calculate_ks_test(expected, actual)
        ks_pvalue = ks_result["p_value"]
        ks_status = "critical" if ks_pvalue < 0.05 else "stable"

        drift_metrics["features"][feature] = {
            "psi": {
                "value": psi_value,
                "status": psi_status,
                "message": f"PSI={psi_value:.4f}"
            },
            "ks_test": {
                "statistic": ks_result["statistic"],
                "p_value": ks_pvalue,
                "status": ks_status,
                "message": f"p={ks_pvalue:.4f}"
            }
        }

        if psi_status == "critical":
            drift_metrics["summary"]["psi_critical"] += 1
        if ks_status == "critical":
            drift_metrics["summary"]["ks_critical"] += 1

    # Determine overall status
    total_critical = (
        drift_metrics["summary"]["psi_critical"] +
        drift_metrics["summary"]["ks_critical"]
    )
    if total_critical > 0:
        drift_metrics["summary"]["overall_status"] = "critical"
    elif any(f["psi"]["status"] == "warning" for f in drift_metrics["features"].values()):
        drift_metrics["summary"]["overall_status"] = "warning"

    return drift_metrics, None


# ═══════════════════════════════════════════════════════════════════════
# DRIFT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

# Check if monitoring is available
if not MONITORING_AVAILABLE:
    st.markdown("""
    <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
        <div style="font-size: 13px; font-weight: 600; color: #856404; margin-bottom: 6px;">⚠️ Monitoring Module Not Available</div>
        <div style="font-size: 11px; color: #856404;">The monitoring module could not be imported. Please ensure src/monitoring.py exists.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Run drift analysis
    drift_metrics, error = compute_drift_analysis()

    if error:
        st.markdown(f"""
        <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
            <div style="font-size: 13px; font-weight: 600; color: #721c24; margin-bottom: 6px;">❌ Error Loading Data</div>
            <div style="font-size: 11px; color: #721c24;">{error}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ═══════════════════════════════════════════════════════════════════════
        # SUMMARY CARD
        # ═══════════════════════════════════════════════════════════════════════

        st.markdown(create_drift_summary_card(drift_metrics), unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════════════════
        # KPI CARDS
        # ═══════════════════════════════════════════════════════════════════════

        summary = drift_metrics["summary"]
        psi_critical = summary["psi_critical"]
        ks_critical = summary["ks_critical"]
        total_features = summary["features_checked"]

        # Count warnings
        warning_count = sum(
            1 for f in drift_metrics["features"].values()
            if f["psi"]["status"] == "warning" or f["ks_test"]["status"] == "warning"
        )

        # Calculate average PSI
        avg_psi = np.mean([f["psi"]["value"] for f in drift_metrics["features"].values()])

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid {PRIMARY}; margin-bottom: 20px; height: 130px; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">📊 Features Checked</div>
                <div style="font-size: 26px; font-weight: 700; color: {PRIMARY}; margin-bottom: 4px;">{total_features}</div>
                <div style="font-size: 10px; color: #757575;">V1-V28 PCA components</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            psi_color = DANGER if psi_critical > 0 else SUCCESS
            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid {DANGER}; margin-bottom: 20px; height: 130px; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">⚠️ Critical PSI</div>
                <div style="font-size: 26px; font-weight: 700; color: {psi_color}; margin-bottom: 4px;">{psi_critical}</div>
                <div style="font-size: 10px; color: #757575;">PSI ≥ 0.2 threshold</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            ks_color = DANGER if ks_critical > 0 else SUCCESS
            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid {WARNING}; margin-bottom: 20px; height: 130px; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">📉 Critical KS Test</div>
                <div style="font-size: 26px; font-weight: 700; color: {ks_color}; margin-bottom: 4px;">{ks_critical}</div>
                <div style="font-size: 10px; color: #757575;">p-value < 0.05 threshold</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            avg_psi_color = DANGER if avg_psi >= 0.2 else WARNING if avg_psi >= 0.1 else SUCCESS
            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid {avg_psi_color}; margin-bottom: 20px; height: 130px; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">📈 Average PSI</div>
                <div style="font-size: 26px; font-weight: 700; color: {avg_psi_color}; margin-bottom: 4px;">{avg_psi:.4f}</div>
                <div style="font-size: 10px; color: #757575;">Mean across all features</div>
            </div>
            """, unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════════════════
        # PSI HEATMAP CHART (Top Drifted Features)
        # ═══════════════════════════════════════════════════════════════════════

        with st.container(border=True):
            st.markdown("**📊 Top Drifted Features (PSI)**")
            st.caption("Distribution shift vs training data (0.1+ = warning, 0.2+ = critical)")
            fig = create_psi_heatmap(drift_metrics, top_n=10, hide_stable=True)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # ═══════════════════════════════════════════════════════════════════════
        # TWO COLUMN LAYOUT: KS TEST + FEATURE TABLE
        # ═══════════════════════════════════════════════════════════════════════

        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                st.markdown("**📉 Top Drifted Features (KS Test)**")
                st.caption("Statistical difference from training (p < 0.05 = drifted)")
                fig = create_ks_test_chart(drift_metrics, top_n=10, hide_stable=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col2:
            st.markdown(create_feature_drift_table(drift_metrics, top_n=10), unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════════════════
        # FULL FEATURE DETAILS (EXPANDER)
        # ═══════════════════════════════════════════════════════════════════════

        with st.expander("📋 View All 28 Features Details", expanded=False):
            # Create full table with all features
            st.markdown(create_feature_drift_table(drift_metrics, top_n=28), unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════════════════
        # INFO SECTION
        # ═══════════════════════════════════════════════════════════════════════

        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                <div style="font-size: 13px; font-weight: 600; color: #333333;">📖 About Drift Detection</div>
            </div>
            <div style="font-size: 11px; color: #757575; line-height: 1.6;">
                <div style="margin-bottom: 8px;"><strong>PSI (Population Stability Index):</strong> Measures feature distribution change between training and production data.</div>
                <div style="margin-bottom: 8px;">• PSI < 0.1: <span style="color: #4CAF50; font-weight: 600;">Stable</span> — No significant drift</div>
                <div style="margin-bottom: 8px;">• 0.1 ≤ PSI < 0.2: <span style="color: #e65100; font-weight: 600;">Warning</span> — Moderate drift, investigate</div>
                <div style="margin-bottom: 20px;">• PSI ≥ 0.2: <span style="color: #F44336; font-weight: 600;">Critical</span> — Significant drift, consider retraining</div>
                <div style="margin-bottom: 8px;"><strong>KS Test (Kolmogorov-Smirnov):</strong> Statistical test comparing distribution shapes. p-value < 0.05 indicates significant difference.</div>
                <div>Data source: Training data from transactions_raw (first 10K rows) · Production data from PostgreSQL prediction_inputs (last 5000 live predictions)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# REFRESH BUTTON
# ═══════════════════════════════════════════════════════════════════════

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("🔄 Refresh Analysis", key="refresh_drift", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
