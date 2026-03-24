"""
Page 4: API Health

Monitor API status, response times, request volume, and errors.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

from dashboard.utils.api_client import check_health, get_api_metrics, format_api_status
from dashboard.utils.data_loader import load_errors_log, get_hourly_stats, get_response_times
from dashboard.utils.charts import create_response_time_chart, create_volume_chart
from dashboard.config import SUCCESS, DANGER, BLUE, inject_shared_styles, build_sidebar


# ═══════════════════════════════════════════════════════════════════════
# SHARED STYLES (must be first)
# ═══════════════════════════════════════════════════════════════════════

inject_shared_styles()

# Build sidebar
build_sidebar(current_page="API Health")


# ═══════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 16px; margin-top: 25px;">
        <div>
            <div style="font-size: 20px; font-weight: 700; color: #333333;">⚕️ API Health Monitoring</div>
            <div style="font-size: 11px; color: #757575; margin-top: 2px;">EC2 instance · 13.61.71.115:8000 · Live checks</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    if st.button("🔄 Ping Now", key="ping_now"):
        st.cache_data.clear()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# STATUS CARDS
# ═══════════════════════════════════════════════════════════════════════

health = check_health()
metrics = get_api_metrics()

col1, col2, col3 = st.columns(3)

with col1:
    api_status = health.get('status', 'unknown')
    status_label, status_class, status_icon = format_api_status(api_status)
    latency = health.get('latency_ms', 0)
    status_color = SUCCESS if status_class == 'dot-green' else DANGER

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid {status_color}; margin-bottom: 12px;">
        <div style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px;">API Status</div>
        <div style="font-size: 13px; font-weight: 600;">
            <span style="display: inline-flex; align-items: center; gap: 5px;"><span style="width: 8px; height: 8px; border-radius: 50%; background: {status_color if status_class == 'dot-green' else DANGER};"></span><span style="color: {status_color};">{status_label}</span></span>
        </div>
        <div style="font-size: 10px; color: #757575; margin-top: 4px;">GET /api/v1/health · {latency}ms</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    model_loaded = health.get('model_loaded', False)
    if model_loaded:
        model_status = "Yes"
        model_color = SUCCESS
    else:
        model_status = "No"
        model_color = DANGER

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid {model_color}; margin-bottom: 12px;">
        <div style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px;">Model Loaded</div>
        <div style="font-size: 13px; font-weight: 600;">
            <span style="display: inline-flex; align-items: center; gap: 5px;"><span style="width: 8px; height: 8px; border-radius: 50%; background: {model_color};"></span><span style="color: {model_color};">{model_status}</span></span>
        </div>
        <div style="font-size: 10px; color: #757575; margin-top: 4px;">{metrics.get('model_name', 'XGBoost')} · In memory</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # Check DB connection status with actual connection attempt
    from dashboard.utils.data_loader import check_db_connection
    db_check = check_db_connection()
    db_connected = db_check['connected']
    db_error = db_check.get('error', '')
    db_color = SUCCESS if db_connected else DANGER
    db_status = "Connected" if db_connected else "Failed"
    db_subtitle = "PostgreSQL · EC2" if db_connected else f"Error: {db_error}"

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 3px solid {db_color}; margin-bottom: 12px;">
        <div style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px;">DB Connection</div>
        <div style="font-size: 13px; font-weight: 600;">
            <span style="display: inline-flex; align-items: center; gap: 5px;"><span style="width: 8px; height: 8px; border-radius: 50%; background: {db_color};"></span><span style="color: {db_color};">{db_status}</span></span>
        </div>
        <div style="font-size: 10px; color: #757575; margin-top: 4px;">{db_subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# RESPONSE TIME CHART
# ═══════════════════════════════════════════════════════════════════════

response_times = get_response_times(limit=100)

if response_times:
    # Single card with header and chart inside
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 600; color: #333333;">📊 Response Time — Last 100 Requests</div>
            <div style="font-size: 11px; color: #757575;">Horizontal line at 200ms SLA threshold</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    fig = create_response_time_chart(response_times)
    st.plotly_chart(fig, use_container_width=False, width=700, config={'displayModeBar': False})
else:
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 600; color: #333333;">📊 Response Time — Last 100 Requests</div>
            <div style="font-size: 11px; color: #757575;">Horizontal line at 200ms SLA threshold</div>
        </div>
        <div style="text-align: center; padding: 40px 20px; color: #757575;">
            <div style="font-size: 32px;">📊</div>
            <div style="font-size: 13px;">No response time data yet</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# REQUEST VOLUME CHART
# ═══════════════════════════════════════════════════════════════════════

hourly_data = get_hourly_stats(hours=24)

if hourly_data['volumes']:
    # Single card with header and chart inside
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 600; color: #333333;">📊 Request Volume — Last 24 Hours</div>
            <div style="font-size: 11px; color: #757575;">Requests per hour from prediction logs</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    fig = create_volume_chart(hourly_data)
    st.plotly_chart(fig, use_container_width=False, width=700, config={'displayModeBar': False})
else:
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 600; color: #333333;">📊 Request Volume — Last 24 Hours</div>
            <div style="font-size: 11px; color: #757575;">Requests per hour from prediction logs</div>
        </div>
        <div style="text-align: center; padding: 40px 20px; color: #757575;">
            <div style="font-size: 32px;">📊</div>
            <div style="font-size: 13px;">No volume data yet</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# ERRORS TABLE
# ═══════════════════════════════════════════════════════════════════════

# Build the entire errors table content as HTML
errors = load_errors_log(limit=20)
table_rows_html = ""

if errors:
    for err in errors[:20]:
        timestamp = err.get('timestamp', '')
        endpoint = err.get('endpoint', 'unknown')
        error_type = err.get('error_type', 'Error')
        message = err.get('error_message', err.get('message', 'No message'))

        # Format timestamp
        if timestamp:
            try:
                import pandas as pd
                ts = pd.to_datetime(timestamp, utc=True)
                time_str = ts.strftime('%H:%M:%S')
            except:
                time_str = str(timestamp)[:8]
        else:
            time_str = 'Unknown'

        table_rows_html += f"""<div style="display: flex; align-items: center; padding: 8px 10px; border-bottom: 1px solid #f0f0f0;"><span style="flex: 0 0 60px; color: #757575; font-size: 11px;">{time_str}</span><span style="flex: 0 0 120px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #4A3C8C;">{endpoint}</span><span style="flex: 0 0 auto; font-family: 'JetBrains Mono', monospace; font-size: 10px; background: rgba(244,67,54,0.08); color: #F44336; padding: 1px 6px; border-radius: 3px;">{error_type}</span><span style="flex: 1; font-size: 11px; color: #757575; padding-left: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{message}">{message[:80]}{'...' if len(str(message)) > 80 else ''}</span></div>"""
else:
    table_rows_html = """<div style="text-align: center; padding: 40px 20px; color: #757575;"><div style="font-size: 32px;">✅</div><div style="font-size: 13px;">No errors logged yet</div></div>"""

# Render the entire card with header and table content together
st.markdown(f"""
<div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <div style="font-size: 13px; font-weight: 600; color: #333333;">🔴 Recent Errors</div>
        <div style="font-size: 11px; color: #757575;">Source: logs/errors.jsonl · Last 20</div>
    </div>
    {table_rows_html}
</div>
""", unsafe_allow_html=True)
