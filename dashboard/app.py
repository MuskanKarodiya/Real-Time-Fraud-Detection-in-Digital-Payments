"""
FraudLens - Fraud Detection Dashboard

Main entry point (Home/Overview page).
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import html

from dashboard.config import (
    inject_shared_styles,
    build_sidebar,
    PAGE_CONFIG,
    API_BASE_URL,
    SUCCESS,
    DANGER,
    PRIMARY,
    BLUE,
    TEXT_SUB,
)
from dashboard.utils.data_loader import (
    get_stats,
    get_high_risk_transactions,
    get_hourly_stats,
    load_model_metadata,
)
from dashboard.utils.api_client import check_health, format_api_status
from dashboard.utils.charts import (
    create_fraud_rate_trend,
)


# ═══════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(**PAGE_CONFIG)


# ═══════════════════════════════════════════════════════════════════════
# SHARED STYLES (must be first)
# ═══════════════════════════════════════════════════════════════════════

inject_shared_styles()


# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════

build_sidebar(current_page="Overview")


# ═══════════════════════════════════════════════════════════════════════
# TOP BAR
# ═══════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div style="height: 48px; background: white; border-bottom: 1px solid #E0E0E0; display: flex; align-items: center; padding: 0 20px; gap: 12px; margin: 0 -20px 20px -20px;">
    <div style="font-size: 15px; font-weight: 700; color: #4A3C8C; flex: 1;">📊 Fraud Detection Dashboard</div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="font-size: 11px; color: #757575;">Last updated: {datetime.now().strftime('%H:%M:%S')}</div>
        <div style="font-size: 11px; color: #4A3C8C; background: rgba(74,60,140,0.08); padding: 4px 10px; border-radius: 4px;">Auto-refresh 5s</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
    <div>
        <div style="font-size: 20px; font-weight: 700; color: #333333;">🏠 Overview</div>
        <div style="font-size: 11px; color: #757575; margin-top: 2px;">Real-time fraud detection system status</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════════════

stats = get_stats()
hourly_data = get_hourly_stats(hours=48)
high_risk = get_high_risk_transactions(limit=10)
health = check_health()


# ═══════════════════════════════════════════════════════════════════════
# KPI CARDS WITH SPARKLINES (Combined in single cards)
# ═══════════════════════════════════════════════════════════════════════

col1, col2, col3, col4 = st.columns(4)

# Prepare data for sparklines
hourly_volumes = hourly_data.get('volumes', [])
hourly_fraud_rates = hourly_data.get('fraud_rates', [])

# Calculate trend for transactions
txn_trend = "—" if len(hourly_volumes) < 2 else ("↑" if hourly_volumes[-1] > hourly_volumes[0] else "↓")
txn_trend_color = SUCCESS if txn_trend == "↑" else DANGER if txn_trend == "↓" else TEXT_SUB

# Calculate trend for fraud rate
fraud_trend = "—" if len(hourly_fraud_rates) < 2 else ("↑" if hourly_fraud_rates[-1] > hourly_fraud_rates[0] else "↓")
fraud_trend_color = DANGER if fraud_trend == "↑" else SUCCESS if fraud_trend == "↓" else TEXT_SUB

# Get response times for latency sparkline
from dashboard.utils.data_loader import get_response_times
response_times = get_response_times(limit=20)
avg_latency = sum(response_times) / len(response_times) if response_times else 0

# Card 1: Total Transactions
with col1:
    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid #4A3C8C; margin-bottom: 12px; height: 130px; display: flex; flex-direction: column; justify-content: center;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em;">📦 Total Transactions</span>
            <span style="font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 3px; background: rgba(76,175,80,0.1); color: {SUCCESS};">{txn_trend}</span>
        </div>
        <div style="font-size: 26px; font-weight: 700; color: #4A3C8C; margin-bottom: 4px;">{stats['total_count']:,}</div>
        <div style="font-size: 10px; color: #757575;">Total predictions logged</div>
    </div>
    """, unsafe_allow_html=True)

# Card 2: Fraud Rate
with col2:
    fraud_rate = stats['fraud_rate']
    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid #FF6B6B; margin-bottom: 12px; height: 130px; display: flex; flex-direction: column; justify-content: center;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em;">⚠️ Fraud Rate</span>
            <span style="font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 3px; background: rgba(244,67,54,0.08); color: {DANGER};">{fraud_trend}</span>
        </div>
        <div style="font-size: 26px; font-weight: 700; color: #FF6B6B; margin-bottom: 4px;">{fraud_rate}%</div>
        <div style="font-size: 10px; color: #757575;">{stats['fraud_count']} flagged fraudulent</div>
    </div>
    """, unsafe_allow_html=True)

# Card 3: API Latency
with col3:
    status_label, status_class, status_icon = format_api_status(health.get('status', 'unknown'))
    status_color = SUCCESS if status_class == 'dot-green' else DANGER

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid {status_color}; margin-bottom: 12px; height: 130px; display: flex; flex-direction: column; justify-content: center;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em;">⚡ API Latency</span>
            <span style="display: inline-flex; align-items: center; gap: 4px;">
                <span style="width: 6px; height: 6px; border-radius: 50%; background: {status_color};"></span>
                <span style="font-size: 10px; font-weight: 600; color: {status_color};">{status_label}</span>
            </span>
        </div>
        <div style="font-size: 26px; font-weight: 700; color: {status_color}; margin-bottom: 4px;">{avg_latency:.0f}ms</div>
        <div style="font-size: 10px; color: #757575;">Average response time</div>
    </div>
    """, unsafe_allow_html=True)

# Card 4: Model Info
with col4:
    metadata = load_model_metadata()
    model_version = metadata.get('model_name', 'v1.0')
    training_date = metadata.get('training_date', '')
    if training_date:
        try:
            dt = datetime.fromisoformat(training_date.replace('Z', '+00:00'))
            date_str = dt.strftime('%b %d')
        except:
            date_str = 'Unknown'
    else:
        date_str = 'Unknown'

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid #2196F3; margin-bottom: 12px; height: 130px; display: flex; flex-direction: column; justify-content: center;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em;">🤖 Model Version</span>
            <span style="font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 3px; background: rgba(33,150,243,0.08); color: #2196F3;">v1.0</span>
        </div>
        <div style="font-size: 26px; font-weight: 700; color: #2196F3; margin-bottom: 4px;">{model_version}</div>
        <div style="font-size: 10px; color: #757575;">XGBoost · {date_str}</div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# FRAUD RATE TREND CHART (Full detailed view)
# ═══════════════════════════════════════════════════════════════════════

# Check if we have enough data points
num_data_points = len(hourly_data.get('volumes', []))

# Only show chart if we have 6+ data points, otherwise show empty state
if num_data_points >= 6:
    with st.container(border=True):
        st.markdown("**📈 Fraud Rate Trend — Last 48 Hours**")
        st.caption("Transaction Volume (bars) + Fraud Rate (line)")
        fig = create_fraud_rate_trend(hourly_data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 600; color: #333333;">📈 Fraud Rate Trend — Last 48 Hours</div>
            <div style="font-size: 11px; color: #757575;">Transaction Volume (bars) + Fraud Rate (line)</div>
        </div>
        <div style="text-align: center; padding: 40px 20px; color: #757575;">
            <div style="font-size: 32px;">📊</div>
            <div style="font-size: 13px; margin-top: 8px;">Not enough data yet</div>
            <div style="font-size: 11px; color: #999999; margin-top: 4px;">Need at least 6 hours of predictions to display trend</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# RECENT HIGH-RISK TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════════

# Build the entire table content as HTML
table_rows_html = ""
if high_risk:
    for txn in high_risk:
        prob = txn.get('fraud_probability', 0)
        prob_color = '#F44336' if prob >= 0.7 else '#e65100' if prob >= 0.3 else '#2e7d32'
        time_ago = txn.get('timestamp', '')
        if time_ago:
            try:
                ts = pd.to_datetime(time_ago, utc=True)
                now = pd.Timestamp.now(tz=timezone.utc)
                delta = (now - ts).total_seconds()
                if delta < 60:
                    time_str = f"{int(delta)} sec ago"
                elif delta < 3600:
                    time_str = f"{int(delta//60)} min ago"
                else:
                    time_str = f"{int(delta//3600)} hr ago"
            except:
                time_str = 'Unknown'
        else:
            time_str = 'Unknown'

        risk_level = txn.get('risk_level', 'UNKNOWN')
        if risk_level == 'HIGH':
            risk_bg = 'rgba(244,67,54,0.1)'
            risk_text = '#F44336'
        elif risk_level == 'MEDIUM':
            risk_bg = 'rgba(255,193,7,0.12)'
            risk_text = '#e65100'
        else:
            risk_bg = 'rgba(76,175,80,0.1)'
            risk_text = '#2e7d32'

        risk_badge = f'<span style="display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 3px; font-weight: 700; font-size: 11px; background: {risk_bg}; color: {risk_text};">{html.escape(risk_level)}</span>'

        table_rows_html += f"""<div style="display: flex; align-items: center; padding: 8px 10px; border-bottom: 1px solid #f0f0f0;"><span style="flex: 1; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #4A3C8C;">{html.escape(txn.get('transaction_id', 'N/A'))}</span><span style="width: 70px; font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 11px; color: {prob_color};">{prob:.4f}</span><span>{risk_badge}</span><span style="color: #757575; font-size: 11px; width: 80px; text-align: right;">{html.escape(time_str)}</span></div>"""
else:
    table_rows_html = """<div style="text-align: center; padding: 40px 20px; color: #757575;"><div style="font-size: 32px;">✅</div><div style="font-size: 13px;">No high-risk transactions detected</div></div>"""

st.markdown(f"""
<div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <div style="font-size: 13px; font-weight: 600; color: #333333;">🔴 Recent High-Risk Transactions</div>
        <div style="font-size: 11px; color: #757575;">Showing last 10 · risk_level = HIGH only</div>
    </div>
    {table_rows_html}
</div>
""", unsafe_allow_html=True)
