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
        title=None,
        hovermode='x unified',
        height=250,
        width=None,  # Responsive width
        margin=dict(l=10, r=10, t=10, b=40),  # Added bottom margin for x labels
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
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

    # Add threshold line
    fig.add_vline(
        x=0.5,
        line_dash='dash',
        line_color=DANGER,
        annotation_text='Threshold 0.5',
        annotation_position='top left',
        annotation_font_size=10,
    )

    fig.update_layout(
        title=None,
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
        title=None,
        height=280,
        width=None,  # Responsive width
        margin=dict(l=0, r=0, t=0, b=40),
        showlegend=True,
        legend=dict(
            orientation='v',
            yanchor='middle',
            y=0.5,
            xanchor='left',
            x=1.01,
            font=dict(size=11)
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
        title=None,
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
        title=None,
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
    <div style="display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 8px 0;">
        <div style="font-size: 10px; color: #757575; font-weight: 600; margin-bottom: 4px;">
            PREDICTED →
        </div>
        <div style="display: flex; gap: 4px; margin-bottom: 4px; padding-left: 26px;">
            <span style="width: 80px; text-align: center; font-size: 10px; color: #757575; font-weight: 600;">Predicted 0</span>
            <span style="width: 80px; text-align: center; font-size: 10px; color: #757575; font-weight: 600;">Predicted 1</span>
        </div>
        <div style="display: flex; gap: 6px; align-items: center;">
            <span style="font-size: 10px; color: #757575; font-weight: 600;">ACTUAL ↓</span>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="font-size: 10px; color: #757575; font-weight: 600; width: 22px;">0</span>
                    <div style="display: flex; gap: 6px;">
                        <div style="width: 80px; height: 72px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; background: #e8eaf6; color: #1a237e;">
                            <div style="font-size: 20px; font-weight: 700;">{tn:,}</div>
                            <div style="font-size: 9px; font-weight: 600; opacity: 0.75;">TN</div>
                        </div>
                        <div style="width: 80px; height: 72px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; background: #ffcdd2; color: #b71c1c;">
                            <div style="font-size: 20px; font-weight: 700;">{fp:,}</div>
                            <div style="font-size: 9px; font-weight: 600; opacity: 0.75;">FP</div>
                        </div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="font-size: 10px; color: #757575; font-weight: 600; width: 22px;">1</span>
                    <div style="display: flex; gap: 6px;">
                        <div style="width: 80px; height: 72px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; background: #ffe0b2; color: #bf360c;">
                            <div style="font-size: 20px; font-weight: 700;">{fn:,}</div>
                            <div style="font-size: 9px; font-weight: 600; opacity: 0.75;">FN</div>
                        </div>
                        <div style="width: 80px; height: 72px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; background: #c8e6c9; color: #1b5e20;">
                            <div style="font-size: 20px; font-weight: 700;">{tp:,}</div>
                            <div style="font-size: 9px; font-weight: 600; opacity: 0.75;">TP</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
