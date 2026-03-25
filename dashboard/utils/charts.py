"""
Chart Builders Module

Creates Plotly charts for the dashboard.
"""
from typing import Dict, List, Any

import plotly.graph_objects as go
import pandas as pd

from dashboard.config import (
    PRIMARY,
    ACCENT,
    SUCCESS,
    WARNING,
    DANGER,
    BLUE,
    TEXT_SUB,
)


def create_sparkline(values: List[float], color: str = PRIMARY, show_area: bool = True) -> go.Figure:
    """
    Create a mini sparkline chart for KPI cards.

    Args:
        values: List of numeric values
        color: Line color
        show_area: Whether to fill area under line

    Returns:
        Plotly Figure
    """
    if not values or len(values) < 2:
        # Return empty figure if not enough data
        fig = go.Figure()
        fig.update_layout(
            height=60,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showgrid=False, showticklabels=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, visible=False),
            paper_bgcolor='white',
            plot_bgcolor='white',
        )
        return fig

    fig = go.Figure()

    # Fill area if requested
    if show_area:
        fig.add_trace(go.Scatter(
            x=list(range(len(values))),
            y=values,
            mode='lines',
            line=dict(color=color, width=1.5),
            fill='tozeroy',
            fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)',
        ))
    else:
        fig.add_trace(go.Scatter(
            x=list(range(len(values))),
            y=values,
            mode='lines',
            line=dict(color=color, width=1.5),
        ))

    # Add trend indicator (up/down arrow based on last vs first)
    if len(values) >= 2:
        trend = values[-1] - values[0]
        trend_color = SUCCESS if trend >= 0 else DANGER
        trend_symbol = '↑' if trend >= 0 else '↓'
    else:
        trend_color = TEXT_SUB
        trend_symbol = '—'

    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, showticklabels=False, visible=False),
        yaxis=dict(showgrid=False, showticklabels=False, visible=False),
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=False,
    )

    return fig


def create_mini_bar_chart(values: List[float], color: str = PRIMARY) -> go.Figure:
    """
    Create a mini bar chart for KPI cards.

    Args:
        values: List of numeric values
        color: Bar color

    Returns:
        Plotly Figure
    """
    if not values:
        fig = go.Figure()
        fig.update_layout(
            height=60,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showgrid=False, showticklabels=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, visible=False),
            paper_bgcolor='white',
            plot_bgcolor='white',
        )
        return fig

    fig = go.Figure(data=[
        go.Bar(
            x=list(range(len(values))),
            y=values,
            marker_color=color,
            marker_line_color='white',
            marker_line_width=0,
        )
    ])

    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, showticklabels=False, visible=False),
        yaxis=dict(showgrid=False, showticklabels=False, visible=False),
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=False,
        bargap=0.1,
    )

    return fig


def create_fraud_rate_trend(hourly_data: Dict[str, Any]) -> go.Figure:
    """
    Create combo chart with transaction volume bars and fraud rate line.

    Args:
        hourly_data: Dict with 'labels', 'volumes', 'fraud_rates'

    Returns:
        Plotly Figure
    """
    labels = hourly_data.get('labels', [])
    volumes = hourly_data.get('volumes', [])
    fraud_rates = hourly_data.get('fraud_rates', [])

    fig = go.Figure()

    # Only create chart if we have data
    if labels and volumes:
        # Bar chart for transaction volume
        fig.add_trace(go.Bar(
            x=labels,
            y=volumes,
            name='Transactions',
            marker_color=PRIMARY,
            opacity=0.7,
            yaxis='y',
            hovertemplate='%{x}<br>Transactions: %{y}<extra></extra>',
        ))

        # Line chart for fraud rate
        fig.add_trace(go.Scatter(
            x=labels,
            y=fraud_rates,
            name='Fraud Rate %',
            mode='lines+markers',
            line=dict(color=ACCENT, width=2),
            marker=dict(size=6),
            yaxis='y2',
            hovertemplate='%{x}<br>Fraud Rate: %{y}%<extra></extra>',
        ))
    else:
        # Empty chart with message
        fig.add_annotation(
            text="No data available yet",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#757575")
        )

    # Layout
    fig.update_layout(
        title=dict(text=''),
        hovermode='x unified',
        height=250,
        width=None,  # Responsive width
        margin=dict(l=10, r=10, t=10, b=40),  # Added bottom margin for x labels
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1,
            xanchor='left',
            x=0,
            font=dict(size=11)
        ),
        xaxis=dict(
            showgrid=False,
            title='Hour',
            tickangle=-45,  # Angled labels for better readability
        ),
        yaxis=dict(
            title='Transactions',
            showgrid=True,
            gridcolor='#f0f0f0',
            side='left',
        ),
        yaxis2=dict(
            title='Fraud Rate %',
            showgrid=False,
            overlaying='y',
            side='right',
            tickformat='.1f',  # Show 1 decimal for percentages
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    return fig


def create_probability_distribution(dist_data: Dict[str, Any]) -> go.Figure:
    """
    Create histogram of fraud probabilities with log scale for visibility.

    Args:
        dist_data: Dict with 'bins' and 'counts'

    Returns:
        Plotly Figure
    """
    bins = dist_data.get('bins', [])
    counts = dist_data.get('counts', [])

    # Color bins based on threshold (0.5)
    colors = [SUCCESS if float(b.split('-')[0]) < 0.5 else DANGER for b in bins]

    # Format counts with commas for display
    text_labels = [f'{c:,}' for c in counts]

    fig = go.Figure(data=[
        go.Bar(
            x=bins,
            y=counts,
            marker_color=colors,
            marker_line_color='white',
            marker_line_width=1,
            text=text_labels,
            textposition='outside',
            textfont=dict(size=10, color='#333333'),
        )
    ])

    # Add threshold line (between bins 0.4-0.5 and 0.5-0.6, so index 4.5)
    fig.add_vline(
        x=4.5,
        line_dash='dash',
        line_color=DANGER,
        annotation_text='Threshold 0.5',
        annotation_position='top left',
        annotation_font_size=10,
    )

    fig.update_layout(
        title=dict(text=''),
        height=250,
        width=None,  # Responsive width
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(
            title='Fraud Probability',
            showgrid=False,
        ),
        yaxis=dict(
            title='Count (Log Scale)',
            showgrid=True,
            gridcolor='#f0f0f0',
            type='log',  # Logarithmic scale to handle extreme imbalance
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        bargap=0.1,
    )

    return fig


def create_risk_pie_chart(risk_counts: Dict[str, int]) -> go.Figure:
    """
    Create pie chart of risk level breakdown.

    Args:
        risk_counts: Dict with 'HIGH', 'MEDIUM', 'LOW' counts

    Returns:
        Plotly Figure
    """
    labels = ['LOW', 'MEDIUM', 'HIGH']
    values = [risk_counts.get(l, 0) for l in labels]
    colors = [SUCCESS, WARNING, DANGER]

    # Filter out zero values
    filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if filtered:
        labels, values, colors = zip(*filtered)

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        textinfo='percent+label',
        textposition='auto',
        hole=0.4,
    )])

    fig.update_layout(
        title=dict(text=''),
        height=320,
        width=None,  # Responsive width
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.15,
            xanchor='center',
            x=0.5,
            font=dict(size=10)
        ),
        paper_bgcolor='white',
    )

    return fig


def create_response_time_chart(response_times: List[float]) -> go.Figure:
    """
    Create line chart of response times.

    Args:
        response_times: List of response times in ms

    Returns:
        Plotly Figure
    """
    fig = go.Figure()

    # Response time line
    fig.add_trace(go.Scatter(
        y=response_times,
        mode='lines',
        line=dict(color=PRIMARY, width=1.5),
        name='Response Time',
    ))

    # 200ms SLA threshold line
    if response_times:
        fig.add_hline(
            y=200,
            line_dash='dash',
            line_color=DANGER,
            annotation_text='SLA 200ms',
            annotation_font_size=9,
        )

    fig.update_layout(
        title=dict(text=''),
        height=200,
        width=None,  # Responsive width
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(
            title='Request',
            showgrid=False,
        ),
        yaxis=dict(
            title='ms',
            showgrid=True,
            gridcolor='#f0f0f0',
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
    )

    return fig


def create_volume_chart(hourly_data: Dict[str, Any]) -> go.Figure:
    """
    Create bar chart of request volume by hour.

    Args:
        hourly_data: Dict with 'labels' and 'volumes'

    Returns:
        Plotly Figure
    """
    fig = go.Figure(data=[
        go.Bar(
            x=hourly_data.get('labels', []),
            y=hourly_data.get('volumes', []),
            marker_color=PRIMARY,
            marker_line_color='white',
            marker_line_width=0.5,
        )
    ])

    fig.update_layout(
        title=dict(text=''),
        height=180,
        width=None,  # Responsive width
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(
            title='Hour',
            showgrid=False,
        ),
        yaxis=dict(
            title='Requests',
            showgrid=True,
            gridcolor='#f0f0f0',
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        bargap=0.2,
    )

    return fig


def create_confusion_matrix_html(tp: int, fp: int, tn: int, fn: int) -> str:
    """
    Create HTML confusion matrix display.

    Args:
        tp: True positives
        fp: False positives
        tn: True negatives
        fn: False negatives

    Returns:
        HTML string for the confusion matrix
    """
    return f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 16px 0; height: 100%;">
        <div style="font-size: 12px; color: #757575; font-weight: 600; margin-bottom: 8px;">
            PREDICTED →
        </div>
        <div style="display: flex; gap: 8px; margin-bottom: 8px; padding-left: 54px;">
            <span style="width: 120px; text-align: center; font-size: 12px; color: #757575; font-weight: 600;">Predicted 0</span>
            <span style="width: 120px; text-align: center; font-size: 12px; color: #757575; font-weight: 600;">Predicted 1</span>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <span style="font-size: 12px; color: #757575; font-weight: 600;">ACTUAL ↓</span>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 12px; color: #757575; font-weight: 600; width: 32px;">0</span>
                    <div style="display: flex; gap: 10px;">
                        <div style="width: 120px; height: 110px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px; background: #e8eaf6; color: #1a237e;">
                            <div style="font-size: 32px; font-weight: 700;">{tn:,}</div>
                            <div style="font-size: 11px; font-weight: 600; opacity: 0.75;">TN</div>
                        </div>
                        <div style="width: 120px; height: 110px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px; background: #ffcdd2; color: #b71c1c;">
                            <div style="font-size: 32px; font-weight: 700;">{fp:,}</div>
                            <div style="font-size: 11px; font-weight: 600; opacity: 0.75;">FP</div>
                        </div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 12px; color: #757575; font-weight: 600; width: 32px;">1</span>
                    <div style="display: flex; gap: 10px;">
                        <div style="width: 120px; height: 110px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px; background: #ffe0b2; color: #bf360c;">
                            <div style="font-size: 32px; font-weight: 700;">{fn:,}</div>
                            <div style="font-size: 11px; font-weight: 600; opacity: 0.75;">FN</div>
                        </div>
                        <div style="width: 120px; height: 110px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px; background: #c8e6c9; color: #1b5e20;">
                            <div style="font-size: 32px; font-weight: 700;">{tp:,}</div>
                            <div style="font-size: 11px; font-weight: 600; opacity: 0.75;">TP</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """


# ============================================================================
# DRIFT MONITORING CHARTS
# ============================================================================

def create_psi_heatmap(drift_metrics: Dict[str, Any], top_n: int = 10, hide_stable: bool = True) -> go.Figure:
    """
    Create horizontal bar chart of PSI values for drifted features.

    Args:
        drift_metrics: Dict with drift analysis results from compute_drift_metrics()
        top_n: Maximum number of features to show (sorted by PSI descending)
        hide_stable: If True, hide stable features (PSI < 0.1)

    Returns:
        Plotly Figure with PSI bar chart
    """
    features = []
    psi_values = []
    psi_statuses = []

    for feature, data in drift_metrics.get("features", {}).items():
        psi_val = data["psi"]["value"]
        psi_status = data["psi"]["status"]

        # Skip stable features if hide_stable is True
        if hide_stable and psi_status == "stable":
            continue

        features.append(feature)
        psi_values.append(psi_val)
        psi_statuses.append(psi_status)

    if not features:
        fig = go.Figure()
        fig.add_annotation(
            text="✅ No drifted features detected",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#4CAF50")
        )
        fig.update_layout(
            height=250,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig

    # Sort by PSI value descending (highest drift first)
    sorted_data = sorted(zip(features, psi_values, psi_statuses), key=lambda x: x[1], reverse=True)
    features, psi_values, psi_statuses = zip(*sorted_data[:top_n])

    # Create color scale based on status
    colors = []
    for status in psi_statuses:
        if status == "stable":
            colors.append(SUCCESS)
        elif status == "warning":
            colors.append(WARNING)
        else:
            colors.append(DANGER)

    fig = go.Figure(data=[
        go.Bar(
            x=psi_values,
            y=features,
            orientation='h',
            marker_color=colors,
            text=[f"{v:.4f}" for v in psi_values],
            textposition='outside',
            marker_line_color='white',
            marker_line_width=1,
            hovertemplate='%{y}<br>PSI: %{x:.4f}<extra></extra>'
        )
    ])

    # Add vertical lines for thresholds
    fig.add_vline(
        x=0.1,
        line_dash='dash',
        line_color=WARNING,
        annotation_text='Warning (0.1)',
        annotation_position='top left',
        annotation_font_size=9
    )
    fig.add_vline(
        x=0.2,
        line_dash='dash',
        line_color=DANGER,
        annotation_text='Critical (0.2)',
        annotation_position='top right',
        annotation_font_size=9
    )

    fig.update_layout(
        title=dict(text=''),
        height=max(250, len(features) * 35),
        width=None,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            title='PSI Value',
            showgrid=True,
            gridcolor='#f0f0f0',
        ),
        yaxis=dict(
            title='Feature',
            showgrid=False,
            automargin=True,
            categoryorder='array',
            categoryarray=list(features)
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
    )

    return fig


def create_ks_test_chart(drift_metrics: Dict[str, Any], top_n: int = 10, hide_stable: bool = True) -> go.Figure:
    """
    Create bar chart of KS test p-values for drifted features.

    Args:
        drift_metrics: Dict with drift analysis results
        top_n: Maximum number of features to show (sorted by p-value ascending)
        hide_stable: If True, hide stable features (p-value >= 0.05)

    Returns:
        Plotly Figure with KS test p-values
    """
    features = []
    p_values = []
    statuses = []

    for feature, data in drift_metrics.get("features", {}).items():
        p_val = data["ks_test"]["p_value"]
        ks_status = data["ks_test"]["status"]

        # Skip stable features if hide_stable is True
        if hide_stable and ks_status == "stable":
            continue

        features.append(feature)
        p_values.append(p_val)
        statuses.append(ks_status)

    if not features:
        fig = go.Figure()
        fig.add_annotation(
            text="✅ No drifted features detected",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#4CAF50")
        )
        fig.update_layout(
            height=250,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig

    # Sort by p-value ascending (lowest p-value = most drifted first)
    sorted_data = sorted(zip(features, p_values, statuses), key=lambda x: x[1])
    features, p_values, statuses = zip(*sorted_data[:top_n])

    # Color based on status
    colors = [DANGER if s == "critical" else SUCCESS for s in statuses]

    fig = go.Figure(data=[
        go.Bar(
            x=p_values,
            y=features,
            orientation='h',
            marker_color=colors,
            text=[f"{v:.4f}" for v in p_values],
            textposition='outside',
            marker_line_color='white',
            marker_line_width=1,
            hovertemplate='%{y}<br>p-value: %{x:.4f}<extra></extra>'
        )
    ])

    # Add threshold line
    fig.add_vline(
        x=0.05,
        line_dash='dash',
        line_color=DANGER,
        annotation_text='Threshold (0.05)',
        annotation_position='bottom right',
        annotation_font_size=9
    )

    fig.update_layout(
        title=dict(text=''),
        height=max(375, len(features) * 35),
        width=None,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            title='KS Test p-value',
            showgrid=True,
            gridcolor='#f0f0f0',
            range=[0, 0.1]
        ),
        yaxis=dict(
            title='Feature',
            showgrid=False,
            automargin=True,
            categoryorder='array',
            categoryarray=list(features)
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
    )

    return fig


def create_drift_summary_card(drift_metrics: Dict[str, Any]) -> str:
    """
    Create HTML summary card for drift analysis.

    Args:
        drift_metrics: Dict with drift analysis results

    Returns:
        HTML string for summary card
    """
    summary = drift_metrics.get("summary", {})
    overall_status = summary.get("overall_status", "unknown")
    psi_critical = summary.get("psi_critical", 0)
    ks_critical = summary.get("ks_critical", 0)
    features_checked = summary.get("features_checked", 0)

    # Count warnings
    warning_count = sum(
        1 for f in drift_metrics.get("features", {}).values()
        if f["psi"]["status"] == "warning" or f["ks_test"]["status"] == "warning"
    )

    # Status styling
    status_colors = {
        "stable": {"bg": "rgba(76,175,80,0.1)", "text": "#2e7d32", "icon": "✓", "border": "#4CAF50"},
        "warning": {"bg": "rgba(255,193,7,0.12)", "text": "#e65100", "icon": "⚠", "border": "#FFC107"},
        "critical": {"bg": "rgba(244,67,54,0.1)", "text": "#F44336", "icon": "✗", "border": "#F44336"}
    }
    style = status_colors.get(overall_status, status_colors["stable"])

    return f"<div style='background: {style['bg']}; border: 1px solid {style['border']}; border-radius: 8px; padding: 16px; margin-bottom: 20px;'><div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;'><div style='font-size: 13px; font-weight: 600; color: {style['text']}; display: flex; align-items: center; gap: 6px;'><span style='font-size: 16px;'>{style['icon']}</span><span>Overall Status: {overall_status.upper()}</span></div></div><div style='display: flex; gap: 20px; flex-wrap: wrap; font-size: 11px; color: #757575;'><div><strong>{features_checked}</strong> features checked</div><div style='width: 1px; height: 14px; background: #E0E0E0;'></div><div><strong style='color: #F44336;'>{psi_critical}</strong> critical PSI</div><div style='width: 1px; height: 14px; background: #E0E0E0;'></div><div><strong style='color: #F44336;'>{ks_critical}</strong> critical KS</div><div style='width: 1px; height: 14px; background: #E0E0E0;'></div><div><strong style='color: #e65100;'>{warning_count}</strong> warnings</div></div></div>"


def create_feature_drift_table(drift_metrics: Dict[str, Any], top_n: int = 15) -> str:
    """
    Create HTML table for feature drift details.

    Args:
        drift_metrics: Dict with drift analysis results
        top_n: Number of top features to show (sorted by PSI)

    Returns:
        HTML string for drift table
    """
    features_data = []
    for feature, data in drift_metrics.get("features", {}).items():
        psi_val = data["psi"]["value"]
        ks_p = data["ks_test"]["p_value"]
        features_data.append({
            "feature": feature,
            "psi": psi_val,
            "psi_status": data["psi"]["status"],
            "ks_pvalue": ks_p,
            "ks_status": data["ks_test"]["status"]
        })

    # Sort by PSI value (descending)
    features_data.sort(key=lambda x: x["psi"], reverse=True)
    features_data = features_data[:top_n]

    if not features_data:
        return """
        <div style="text-align: center; padding: 20px; color: #757575;">
            No drift data available
        </div>
        """

    rows = []
    for item in features_data:
        # PSI badge
        psi_colors = {
            "stable": ("#2e7d32", "rgba(76,175,80,0.1)"),
            "warning": ("#e65100", "rgba(255,193,7,0.12)"),
            "critical": ("#F44336", "rgba(244,67,54,0.1)")
        }
        psi_text, psi_bg = psi_colors.get(item["psi_status"], psi_colors["stable"])

        # KS badge
        ks_text, ks_bg = psi_colors.get(item["ks_status"], psi_colors["stable"])

        rows.append(f"<tr style='border-bottom: 1px solid #f0f0f0;'><td style='padding: 8px; font-family: JetBrains Mono, monospace; font-size: 11px; color: #4A3C8C;'>{item['feature']}</td><td style='padding: 8px; text-align: center;'><span style='background: {psi_bg}; color: {psi_text}; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 600;'>{item['psi']:.4f}</span></td><td style='padding: 8px; text-align: center;'><span style='background: {ks_bg}; color: {ks_text}; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 600;'>{item['ks_pvalue']:.4f}</span></td></tr>")

    return f"<div style='background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 20px;'><div style='font-size: 13px; font-weight: 600; color: #333333; margin-bottom: 4px;'>🔍 Top Drifted Features</div><div style='font-size: 11px; color: #757575; margin-bottom: 12px;'>Sorted by PSI value</div><div style='overflow-x: auto;'><table style='width: 100%; border-collapse: collapse; font-size: 11px;'><thead><tr style='border-bottom: 2px solid #E0E0E0;'><th style='padding: 8px; text-align: left; color: #757575; font-weight: 600;'>Feature</th><th style='padding: 8px; text-align: center; color: #757575; font-weight: 600;'>PSI Value</th><th style='padding: 8px; text-align: center; color: #757575; font-weight: 600;'>KS p-value</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>"


def create_performance_trend_chart(performance_history: List[Dict[str, Any]]) -> go.Figure:
    """
    Create line chart of performance metrics over time.

    Args:
        performance_history: List of dicts with timestamp and metrics

    Returns:
        Plotly Figure with performance trends
    """
    if not performance_history:
        fig = go.Figure()
        fig.add_annotation(
            text="No performance history available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#757575")
        )
        fig.update_layout(
            height=250,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig

    timestamps = [pd.to_datetime(p.get("timestamp")) for p in performance_history]
    precision = [p.get("precision", 0) for p in performance_history]
    recall = [p.get("recall", 0) for p in performance_history]
    f1 = [p.get("f1_score", 0) for p in performance_history]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=precision,
        mode='lines+markers',
        name='Precision',
        line=dict(color=BLUE, width=2),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=recall,
        mode='lines+markers',
        name='Recall',
        line=dict(color=WARNING, width=2),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=f1,
        mode='lines+markers',
        name='F1 Score',
        line=dict(color=PRIMARY, width=2),
        marker=dict(size=6)
    ))

    # Add threshold lines
    fig.add_hline(
        y=0.85,
        line_dash='dash',
        line_color=SUCCESS,
        annotation_text='Target (0.85)',
        annotation_position='top right',
        annotation_font_size=8
    )

    fig.update_layout(
        title=dict(text=''),
        height=250,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(
            title='Date',
            showgrid=False,
        ),
        yaxis=dict(
            title='Score',
            showgrid=True,
            gridcolor='#f0f0f0',
            range=[0, 1]
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='left',
            x=0,
            font=dict(size=11)
        ),
        hovermode='x unified',
    )

    return fig
