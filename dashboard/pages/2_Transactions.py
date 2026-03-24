"""
Page 3: Transactions

Browse, filter, and export prediction logs with live prediction test.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import numpy as np

from dashboard.utils.data_loader import load_predictions_dataframe, get_stats
from dashboard.utils.api_client import make_prediction
from dashboard.utils.feature_preprocessing import (
    preprocess_features,
    prepare_api_payload,
    get_example_payload
)
from dashboard.config import (
    RISK_HIGH_BG, RISK_MEDIUM_BG, RISK_LOW_BG,
    RISK_HIGH_TEXT, RISK_MEDIUM_TEXT, RISK_LOW_TEXT,
    API_BASE_URL,
    inject_shared_styles,
    build_sidebar
)


# ═══════════════════════════════════════════════════════════════════════
# SHARED STYLES (must be first)
# ═══════════════════════════════════════════════════════════════════════

inject_shared_styles()

# Build sidebar
build_sidebar(current_page="Transactions")


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS (defined before use)
# ═══════════════════════════════════════════════════════════════════════

def display_prediction_result(result):
    """Display prediction result with proper formatting."""
    if result.get("error"):
        error_msg = result.get('message', 'Unknown error')
        st.error(f"❌ Prediction failed: {error_msg}")

        # Show helpful hints
        st.markdown("""
        <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 12px; margin-top: 12px;">
            <div style="font-size: 12px; font-weight: 600; color: #856404; margin-bottom: 6px;">💡 Troubleshooting Tips:</div>
            <ul style="font-size: 11px; color: #856404; margin: 0; padding-left: 16px;">
                <li>Check if the API server is running at <code>{API_BASE_URL}</code></li>
                <li>Try the example transactions above - they use real dataset values</li>
                <li>Check your internet connection</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        prob = result.get('fraud_probability', 0)
        risk = result.get('risk_level', 'UNKNOWN')
        rt = result.get('response_time_ms', 0)

        # Display result
        prob_color = '#F44336' if prob >= 0.7 else '#e65100' if prob >= 0.3 else '#2e7d32'

        # Risk badge
        risk_bg = RISK_HIGH_BG if risk == 'HIGH' else RISK_MEDIUM_BG if risk == 'MEDIUM' else RISK_LOW_BG
        risk_text = RISK_HIGH_TEXT if risk == 'HIGH' else RISK_MEDIUM_TEXT if risk == 'MEDIUM' else RISK_LOW_TEXT
        risk_badge = f'<span style="display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 3px; font-weight: 700; font-size: 11px; background: {risk_bg}; color: {risk_text};">{risk}</span>'

        st.markdown(f"""
        <div style="background: #f8f9ff; border: 1px solid rgba(74,60,140,0.2); border-radius: 6px; padding: 12px; display: flex; gap: 20px; align-items: center; flex-wrap: wrap; margin-top: 12px;">
            <div style="display: flex; flex-direction: column; gap: 3px;">
                <span style="font-size: 10px; color: #757575; text-transform: uppercase; letter-spacing: 0.06em;">Fraud Probability</span>
                <span style="font-size: 16px; font-weight: 700; color: {prob_color};">{prob:.4f}</span>
            </div>
            <div style="width: 1px; height: 30px; background: #E0E0E0;"></div>
            <div style="display: flex; flex-direction: column; gap: 3px;">
                <span style="font-size: 10px; color: #757575; text-transform: uppercase; letter-spacing: 0.06em;">Risk Level</span>
                <span>{risk_badge}</span>
            </div>
            <div style="width: 1px; height: 30px; background: #E0E0E0;"></div>
            <div style="display: flex; flex-direction: column; gap: 3px;">
                <span style="font-size: 10px; color: #757575; text-transform: uppercase; letter-spacing: 0.06em;">Prediction</span>
                <span style="font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{result.get('prediction', 0)} ({"Legitimate" if result.get('prediction') == 0 else "Fraud"})</span>
            </div>
            <div style="width: 1px; height: 30px; background: #E0E0E0;"></div>
            <div style="display: flex; flex-direction: column; gap: 3px;">
                <span style="font-size: 10px; color: #757575; text-transform: uppercase; letter-spacing: 0.06em;">Response Time</span>
                <span style="font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{rt:.0f}ms</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; margin-top: 20px;">
    <div>
        <div style="font-size: 20px; font-weight: 700; color: #333333;">🔍 Transaction Explorer</div>
        <div style="font-size: 11px; color: #757575; margin-top: 2px;">Browse, filter and export prediction logs</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# FILTER BAR
# ═══════════════════════════════════════════════════════════════════════

col1, col2, col3, col4 = st.columns([1, 1, 2, 1])

with col1:
    time_range = st.selectbox(
        "Time Range",
        ["All Time", "Last 24h", "Last 7 days", "Last 30 days"]
    )

with col2:
    risk_filter = st.selectbox(
        "Risk Level",
        ["All", "LOW", "MEDIUM", "HIGH"]
    )

with col3:
    search_query = st.text_input(
        "Search Transaction ID",
        placeholder="e.g. txn_88210..."
    )

with col4:
    # Download button will be populated after data is loaded
    export_placeholder = st.empty()


# ═══════════════════════════════════════════════════════════════════════
# LOAD DATA WITH FILTERS
# ═══════════════════════════════════════════════════════════════════════

df = load_predictions_dataframe()

# Apply filters
if not df.empty:
    # Time range filter
    if time_range != "All Time":
        now = pd.Timestamp.now(tz=timezone.utc)
        if time_range == "Last 24h":
            cutoff = now - pd.Timedelta(hours=24)
        elif time_range == "Last 7 days":
            cutoff = now - pd.Timedelta(days=7)
        elif time_range == "Last 30 days":
            cutoff = now - pd.Timedelta(days=30)
        df = df[df['timestamp'] >= cutoff].copy()

    # Risk level filter
    if risk_filter != "All":
        df = df[df['risk_level'] == risk_filter].copy()

    # Search filter
    if search_query:
        df = df[df['transaction_id'].str.contains(search_query, case=False, na=False)].copy()


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY BAR
# ═══════════════════════════════════════════════════════════════════════

stats = get_stats()
total = len(df)
avg_prob = df['fraud_probability'].mean() if not df.empty and 'fraud_probability' in df.columns else 0
avg_rt = df['response_time_ms'].mean() if not df.empty and 'response_time_ms' in df.columns else 0

risk_counts = df['risk_level'].value_counts().to_dict() if not df.empty and 'risk_level' in df.columns else {}

st.markdown(f"""
<div style="background: rgba(74,60,140,0.08); border: 1px solid rgba(74,60,140,0.15); border-radius: 6px; padding: 8px 14px; display: flex; gap: 20px; align-items: center; flex-wrap: wrap; font-size: 11px; color: #4A3C8C; margin-bottom: 12px;">
    <div style="display: flex; align-items: center; gap: 4px;"><strong>{total:,}</strong> transactions</div>
    <div style="width: 1px; height: 14px; background: rgba(74,60,140,0.2);"></div>
    <div style="display: flex; align-items: center; gap: 4px;">Avg fraud prob: <strong>{avg_prob:.3f}</strong></div>
    <div style="width: 1px; height: 14px; background: rgba(74,60,140,0.2);"></div>
    <div style="display: flex; align-items: center; gap: 4px;">Avg response time: <strong>{avg_rt:.1f}ms</strong></div>
    <div style="width: 1px; height: 14px; background: rgba(74,60,140,0.2);"></div>
    <div style="display: flex; align-items: center; gap: 4px;">HIGH risk: <strong style="color: #F44336;">{risk_counts.get('HIGH', 0)}</strong></div>
    <div style="width: 1px; height: 14px; background: rgba(74,60,140,0.2);"></div>
    <div style="display: flex; align-items: center; gap: 4px;">MEDIUM: <strong style="color: #e65100;">{risk_counts.get('MEDIUM', 0)}</strong></div>
    <div style="width: 1px; height: 14px; background: rgba(74,60,140,0.2);"></div>
    <div style="display: flex; align-items: center; gap: 4px;">LOW: <strong style="color: #4CAF50;">{risk_counts.get('LOW', 0)}</strong></div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# EXPORT CSV BUTTON
# ═══════════════════════════════════════════════════════════════════════

# Convert filtered dataframe to CSV
csv_data = df.to_csv(index=False)

with export_placeholder:
    st.download_button(
        label="⬇ Export CSV",
        data=csv_data,
        file_name="transactions_export.csv",
        mime="text/csv",
        use_container_width=True
    )


# ═══════════════════════════════════════════════════════════════════════
# DATA TABLE
# ═══════════════════════════════════════════════════════════════════════

# Build the entire table content as HTML
table_content_html = ""

if df.empty:
    table_content_html = """<div style="text-align: center; padding: 40px 20px; color: #757575;"><div style="font-size: 32px;">📋</div><div style="font-size: 13px;">No transactions match your filters</div></div>"""
else:
    # Show only 10 most recent rows
    display_df = df.head(10).copy()

    # Table header
    table_content_html += """<div style="display: flex; align-items: center; padding: 8px 10px; border-bottom: 2px solid #E0E0E0; font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase;"><span style="flex: 0 0 120px;">Transaction ID</span><span style="flex: 0 0 90px;">Timestamp</span><span style="flex: 0 0 70px;">Amount</span><span style="flex: 0 0 60px;">Fraud %</span><span style="flex: 0 0 70px;">Risk</span><span style="flex: 1; text-align: right;">Response Time</span></div>"""

    # Format for display
    for _, row in display_df.iterrows():
        prob = row.get('fraud_probability', 0)
        prob_color = '#F44336' if prob >= 0.7 else '#e65100' if prob >= 0.3 else '#2e7d32'
        prob_str = f'{prob:.2%}'

        timestamp = row.get('timestamp', '')
        if timestamp and pd.notna(timestamp):
            try:
                ts = pd.to_datetime(timestamp)
                time_str = ts.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = str(timestamp)[:19]
        else:
            time_str = 'Unknown'

        amount = row.get('amount')
        amount_str = f'${amount:,.2f}' if amount and pd.notna(amount) else 'N/A'

        rt = row.get('response_time_ms')
        rt_str = f'{rt:.0f}ms' if rt and pd.notna(rt) else 'N/A'

        # Risk badge HTML
        risk = row.get('risk_level', 'UNKNOWN')
        risk_bg = RISK_HIGH_BG if risk == 'HIGH' else RISK_MEDIUM_BG if risk == 'MEDIUM' else RISK_LOW_BG
        risk_text = RISK_HIGH_TEXT if risk == 'HIGH' else RISK_MEDIUM_TEXT if risk == 'MEDIUM' else RISK_LOW_TEXT
        risk_badge = f'<span style="display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 3px; font-weight: 700; font-size: 11px; background: {risk_bg}; color: {risk_text};">{risk}</span>'

        table_content_html += f"""<div style="display: flex; align-items: center; padding: 8px 10px; border-bottom: 1px solid #f0f0f0;"><span style="flex: 0 0 120px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #4A3C8C; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{row.get('transaction_id', 'N/A')}">{row.get('transaction_id', 'N/A')}</span><span style="flex: 0 0 90px; font-size: 11px; color: #757575;">{time_str}</span><span style="flex: 0 0 70px; font-size: 11px;">{amount_str}</span><span style="flex: 0 0 60px; font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 11px; color: {prob_color};">{prob_str}</span><span style="flex: 0 0 70px;">{risk_badge}</span><span style="flex: 1; text-align: right; font-size: 11px; color: #757575;">{rt_str}</span></div>"""

    # Row count info
    total_rows = len(df)
    if total_rows > 10:
        table_content_html += f"""<div style="display: flex; align-items: center; justify-content: center; margin-top: 12px; padding-top: 12px; border-top: 1px solid #E0E0E0; font-size: 11px; color: #757575;">Showing latest 10 of {total_rows:,} total transactions</div>"""

# Render the entire card with header and table content together
st.markdown(f"""
<div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <div style="font-size: 13px; font-weight: 600; color: #333333;">📋 Transaction List</div>
        <div style="font-size: 11px; color: #757575;">Showing latest 10 rows</div>
    </div>
    {table_content_html}
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# TEST PREDICTION (COLLAPSIBLE)
# ═══════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
""", unsafe_allow_html=True)

# Use Streamlit's expander for collapsible
with st.expander("🧪 Live Prediction Test", expanded=False):
    # Selection for test data source
    test_mode = st.radio(
        "Select Test Data Source",
        ["📊 Example from Real Dataset", "🎲 Random Features (Demo)", "📝 Manual Input"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if test_mode == "📊 Example from Real Dataset":
        st.info("📊 Real examples from the creditcard.csv dataset - click a button to test")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔴 Test FRAUD Case", key="btn_fraud", use_container_width=True):
                import uuid
                payload = get_example_payload("fraud")
                txn_id = f"test_fraud_{uuid.uuid4().hex[:8]}"

                # Show what values are being used
                st.markdown("---")
                st.markdown("### 📋 Transaction Details")
                st.markdown(f"**Amount:** ${payload['amount']:.2f}")
                st.markdown(f"**Features (V1-V5):** {payload['features'][:5]}")
                st.markdown(f"**All Features (31):** `{len(payload['features'])}` values")
                with st.expander("View Full Features"):
                    st.json(payload)

                with st.spinner(f"Calling {API_BASE_URL}..."):
                    result = make_prediction(txn_id, payload['amount'], payload['features'], "demo-key")
                display_prediction_result(result)

        with col2:
            if st.button("🟢 Test LEGITIMATE Case", key="btn_legit", use_container_width=True):
                import uuid
                payload = get_example_payload("legitimate")
                txn_id = f"test_legit_{uuid.uuid4().hex[:8]}"

                # Show what values are being used
                st.markdown("---")
                st.markdown("### 📋 Transaction Details")
                st.markdown(f"**Amount:** ${payload['amount']:.2f}")
                st.markdown(f"**Features (V1-V5):** {payload['features'][:5]}")
                st.markdown(f"**All Features (31):** `{len(payload['features'])}` values")
                with st.expander("View Full Features"):
                    st.json(payload)

                with st.spinner(f"Calling {API_BASE_URL}..."):
                    result = make_prediction(txn_id, payload['amount'], payload['features'], "demo-key")
                display_prediction_result(result)

        with col3:
            if st.button("🟡 Test BORDERLINE Case", key="btn_borderline", use_container_width=True):
                import uuid
                payload = get_example_payload("borderline")
                txn_id = f"test_borderline_{uuid.uuid4().hex[:8]}"

                # Show what values are being used
                st.markdown("---")
                st.markdown("### 📋 Transaction Details")
                st.markdown(f"**Amount:** ${payload['amount']:.2f}")
                st.markdown(f"**Features (V1-V5):** {payload['features'][:5]}")
                st.markdown(f"**All Features (31):** `{len(payload['features'])}` values")
                with st.expander("View Full Features"):
                    st.json(payload)

                with st.spinner(f"Calling {API_BASE_URL}..."):
                    result = make_prediction(txn_id, payload['amount'], payload['features'], "demo-key")
                display_prediction_result(result)

    elif test_mode == "🎲 Random Features (Demo)":
        st.info("🎲 Demo mode: Generates random V1-V28 features and computes derived features automatically")

        amount = st.number_input(
            "Amount ($)",
            min_value=0.01,
            max_value=100000.0,
            value=150.0,
            step=10.0,
            format="%.2f",
            key="demo_amount"
        )

        time_elapsed = st.number_input(
            "Time Elapsed (seconds from first transaction)",
            min_value=0.0,
            max_value=172800.0,  # 48 hours
            value=0.0,
            step=1.0,
            help="Time since first transaction in the dataset",
            key="demo_time"
        )

        if st.button("🎲 Generate Random & Predict", key="run_random_demo"):
            import uuid
            # Generate random V1-V28 features (simulating PCA components)
            v_features = [np.random.uniform(-3, 3) for _ in range(28)]

            # Preprocess to get all 31 features
            all_31_features = preprocess_features(v_features, amount, time_elapsed)

            txn_id = f"demo_{uuid.uuid4().hex[:8]}"
            with st.spinner(f"Calling {API_BASE_URL}..."):
                result = make_prediction(txn_id, amount, all_31_features, "demo-key")

            display_prediction_result(result)

    else:  # Manual Input
        st.info("📝 Enter raw transaction data - the system will compute derived features automatically")

        amount = st.number_input(
            "Amount ($)",
            min_value=0.01,
            max_value=10000000.0,
            value=150.0,
            step=10.0,
            format="%.2f",
            key="manual_amount"
        )

        time_elapsed = st.number_input(
            "Time Elapsed (seconds)",
            min_value=0.0,
            max_value=172800.0,
            value=0.0,
            step=1.0,
            help="Time since first transaction (0 = current time)",
            key="manual_time"
        )

        st.markdown("**Enter 28 PCA Features (V1-V28):**")
        st.markdown("<small>Enter comma-separated values for V1 through V28 from the dataset</small>", unsafe_allow_html=True)

        v_input = st.text_input(
            "V1-V28 (comma-separated)",
            placeholder="-1.36, -0.07, 2.54, 1.38, -0.34, 0.46, 0.24, 0.10, ...",
            help="28 PCA features from the credit card dataset"
        )

        if st.button("🔮 Run Prediction", key="run_manual", type="primary"):
            try:
                # Parse V features
                v_features = [float(x.strip()) for x in v_input.split(',')]

                if len(v_features) != 28:
                    st.error(f"❌ Expected 28 V features (V1-V28), got {len(v_features)}")
                else:
                    import uuid
                    # Preprocess to get all 31 features
                    all_31_features = preprocess_features(v_features, amount, time_elapsed)

                    txn_id = f"manual_{uuid.uuid4().hex[:8]}"
                    with st.spinner(f"Calling {API_BASE_URL}..."):
                        result = make_prediction(txn_id, amount, all_31_features, "demo-key")

                    display_prediction_result(result)

            except ValueError:
                st.error("❌ Invalid number format. Please enter comma-separated numbers.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

st.markdown("</div>", unsafe_allow_html=True)
