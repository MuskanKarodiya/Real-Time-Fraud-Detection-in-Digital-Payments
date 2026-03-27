"""
Page 2: Model Performance

Shows model metrics, probability distribution, risk breakdown, and confusion matrix.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from datetime import datetime

from dashboard.utils.data_loader import load_model_metadata, get_probability_distribution, get_stats
from dashboard.utils.charts import create_probability_distribution, create_risk_pie_chart, create_confusion_matrix_html
from dashboard.config import SUCCESS, DANGER, inject_shared_styles, build_sidebar, card_header


# ═══════════════════════════════════════════════════════════════════════
# SHARED STYLES (must be first)
# ═══════════════════════════════════════════════════════════════════════

inject_shared_styles()

# Build sidebar
build_sidebar(current_page="Model Performance")


# ═══════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════

metadata = load_model_metadata()
model_name = metadata.get('model_name', 'Fraud Detector v1.0')
training_date = metadata.get('training_date', '')

try:
    dt = datetime.fromisoformat(training_date.replace('Z', '+00:00'))
    date_str = dt.strftime('%B %d, %Y')
except:
    date_str = 'Unknown'

st.markdown(f"""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; margin-top: 20px;">
    <div>
        <div style="font-size: 20px; font-weight: 700; color: #333333;">📊 Model Performance</div>
        <div style="font-size: 11px; color: #757575; margin-top: 2px;">Metrics from models/metadata.json · {model_name}</div>
    </div>
    <div style="font-size: 11px; color: #757575;">
        Trained: {date_str}
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# METRIC CARDS
# ═══════════════════════════════════════════════════════════════════════

metrics = metadata.get('metrics', {})

col1, col2, col3, col4 = st.columns(4)

# Define targets and actual values
metric_configs = [
    {
        'name': 'ROC-AUC',
        'value': metrics.get('roc_auc', 0),
        'target': 0.95,
        'format': '.2%',
        'color': SUCCESS
    },
    {
        'name': 'Precision',
        'value': metrics.get('precision', 0),
        'target': 0.85,
        'format': '.2%',
        'color': SUCCESS
    },
    {
        'name': 'Recall',
        'value': metrics.get('recall', 0),
        'target': 0.85,
        'format': '.2%',
        'color': DANGER
    },
    {
        'name': 'F1 Score',
        'value': metrics.get('f1_score', 0),
        'target': None,
        'format': '.2%',
        'color': '#2196F3'
    },
]

for i, config in enumerate(metric_configs):
    col = [col1, col2, col3, col4][i]
    value = config['value']
    target = config['target']

    # Format value
    if config['name'] == 'ROC-AUC':
        value_str = f"{value:.2%}"
    else:
        value_str = f"{value:.2%}"

    # Check if passes target
    if target is not None:
        passes = value >= target
        pass_bg = "rgba(76,175,80,0.1)" if passes else "rgba(244,67,54,0.08)"
        pass_color = "#2e7d32" if passes else "#F44336"
        pass_label = "✓ Pass" if passes else "✗ Fail"
        pass_html = f'<span style="display: inline-flex; align-items: center; gap: 4px; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 3px; margin-bottom: 4px; background: {pass_bg}; color: {pass_color};">{pass_label}</span>'
        target_html = f'<div style="font-size: 9px; color: #757575;">Target ≥ {target:.0%}</div>'
    else:
        pass_html = '<span style="display: inline-flex; align-items: center; gap: 4px; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 3px; margin-bottom: 4px; background: rgba(33,150,243,0.08); color: #1565c0;">— No Target</span>'
        target_html = '<div style="font-size: 9px; color: #757575;">Harmonic mean</div>'

    with col:
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px; height: 100%;">
            <div style="font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">{config['name']}</div>
            <div style="font-size: 26px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 6px; color: {config['color']};">{value_str}</div>
            <div>{pass_html}</div>
            {target_html}
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# PROBABILITY DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════

dist_data = get_probability_distribution()
chart_content = ""

if dist_data['bins']:
    with st.container(border=True):
        st.markdown("**📊 Fraud Probability Distribution**")
        st.caption("From prediction logs · Threshold at 0.5")
        fig = create_probability_distribution(dist_data)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 600; color: #333333;">📊 Fraud Probability Distribution</div>
            <div style="font-size: 11px; color: #757575;">From prediction logs · Threshold at 0.5</div>
        </div>
        <div style="text-align: center; padding: 40px 20px; color: #757575;">
            <div style="font-size: 32px;">📊</div>
            <div style="font-size: 13px;">No distribution data available yet</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# RISK BREAKDOWN + CONFUSION MATRIX
# ═══════════════════════════════════════════════════════════════════════

col1, col2 = st.columns(2)

stats = get_stats()

with col1:
    risk_counts = stats['risk_counts']

    if sum(risk_counts.values()) > 0:
        with st.container(border=True):
            st.markdown("**🥧 Risk Level Breakdown**")
            st.caption("From prediction logs")
            fig = create_risk_pie_chart(risk_counts)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div style="font-size: 13px; font-weight: 600; color: #333333;">🥧 Risk Level Breakdown</div>
                <div style="font-size: 11px; color: #757575;">From prediction logs</div>
            </div>
            <div style="text-align: center; padding: 40px 20px; color: #757575;">
                <div style="font-size: 32px;">🥧</div>
                <div style="font-size: 13px;">No risk data available</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    # Confusion Matrix from training evaluation (Test Set: n=56,962)
    # Source: notebooks/06_model_card_and_evaluation.ipynb
    tp = 83   # True Positives (Fraud correctly identified)
    fp = 13   # False Positives (Legit incorrectly flagged)
    tn = 56851   # True Negatives (Legit correctly identified)
    fn = 15   # False Negatives (Fraud missed)
    cm_content = create_confusion_matrix_html(tp, fp, tn, fn)

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px; min-height: 432px; display: flex; flex-direction: column;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 600; color: #333333;">🔲 Confusion Matrix</div>
            <div style="font-size: 11px; color: #757575;">Based on model training performance</div>
        </div>
        <div style="flex: 1; display: flex; flex-direction: column; justify-content: center;">{cm_content}</div>
    </div>
    """, unsafe_allow_html=True)
