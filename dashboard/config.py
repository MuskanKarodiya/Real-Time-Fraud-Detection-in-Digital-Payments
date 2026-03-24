"""
Dashboard Configuration

Design system constants matching the approved mockup.
"""
import os

# ═══════════════════════════════════════════════════════════════════════
# COLORS (Light Theme)
# ═══════════════════════════════════════════════════════════════════════

# Backgrounds
BG_PAGE = "#F0F2F6"          # Page background
BG_SIDEBAR = "#FFFFFF"       # Sidebar white
BG_CARD = "#FFFFFF"          # Card white

# Primary Colors
PRIMARY = "#4A3C8C"          # Deep purple - primary actions
PRIMARY_LIGHT = "#6254a8"    # Light purple - hover
PRIMARY_BG = "rgba(74,60,140,0.08)"  # Primary background tint

# Status/Risk Colors
ACCENT = "#FF6B6B"           # Red/coral - fraud alerts
SUCCESS = "#4CAF50"          # Green - healthy, LOW risk
WARNING = "#FFC107"          # Yellow - MEDIUM risk
DANGER = "#F44336"           # Red - HIGH risk, errors
BLUE = "#2196F3"             # Blue - API status, info

# Text Colors
TEXT = "#333333"             # Main text
TEXT_SUB = "#757575"         # Secondary text
TEXT_MUTED = "#999999"       # Muted text

# Borders
BORDER = "#E0E0E0"           # Card borders
BORDER_FOCUS = "#4A3C8C"     # Focus state

# Risk Badge Colors
RISK_HIGH_BG = "rgba(244,67,54,0.1)"
RISK_HIGH_TEXT = "#F44336"
RISK_MEDIUM_BG = "rgba(255,193,7,0.12)"
RISK_MEDIUM_TEXT = "#e65100"
RISK_LOW_BG = "rgba(76,175,80,0.1)"
RISK_LOW_TEXT = "#2e7d32"

# ═══════════════════════════════════════════════════════════════════════
# TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════════════

FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Consolas', 'Monaco', monospace"

# Font Sizes
FONT_PAGE_TITLE = "20px"
FONT_SECTION_HEADER = "13px"
FONT_BODY = "13px"
FONT_SMALL = "11px"
FONT_TINY = "10px"

# ═══════════════════════════════════════════════════════════════════════
# SPACING & SIZING
# ═══════════════════════════════════════════════════════════════════════

CARD_PADDING = "16px"
SECTION_GAP = "18px"
BORDER_RADIUS_CARD = "8px"
BORDER_RADIUS_BUTTON = "4px"

# KPI Card Border Colors
KPI_BORDER_PURPLE = "#4A3C8C"
KPI_BORDER_RED = "#FF6B6B"
KPI_BORDER_GREEN = "#4CAF50"
KPI_BORDER_BLUE = "#2196F3"

# ═══════════════════════════════════════════════════════════════════════
# FILE PATHS
# ═══════════════════════════════════════════════════════════════════════

from pathlib import Path

# Root directory (project root)
BASE_DIR = Path(__file__).parent.parent

# Data files
PREDICTIONS_LOG = BASE_DIR / "logs" / "predictions.jsonl"
ERRORS_LOG = BASE_DIR / "logs" / "errors.jsonl"
MODEL_METADATA = BASE_DIR / "models" / "metadata.json"

# ═══════════════════════════════════════════════════════════════════════
# API CONFIG
# ═══════════════════════════════════════════════════════════════════════

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = 10  # seconds

# ═══════════════════════════════════════════════════════════════════════
# CUSTOM CSS
# ═══════════════════════════════════════════════════════════════════════

CUSTOM_CSS = f"""
<style>
/* ═══════════════════════════════════════════════════════════════════════
   GLOBAL STYLES
═══════════════════════════════════════════════════════════════════════ */
body {{
    font-family: {FONT_FAMILY};
}}

/* Hide Streamlit's default footer */
footer {{visibility: hidden;}}

/* ═══════════════════════════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: {BG_SIDEBAR};
    border-right: 1px solid {BORDER};
}}

/* ═══════════════════════════════════════════════════════════════════════
   CARDS
═══════════════════════════════════════════════════════════════════════ */
.card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {BORDER_RADIUS_CARD};
    padding: {CARD_PADDING};
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    margin-bottom: 12px;
}}

.card-title {{
    font-size: {FONT_SECTION_HEADER};
    font-weight: 600;
    color: {TEXT};
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.card-subtitle {{
    font-size: 11px;
    color: {TEXT_SUB};
    font-weight: 400;
}}

/* ═══════════════════════════════════════════════════════════════════════
   KPI CARDS
═══════════════════════════════════════════════════════════════════════ */
.kpi-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {BORDER_RADIUS_CARD};
    padding: {CARD_PADDING};
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid {BORDER};
}}

.kpi-card-purple {{ border-top-color: {KPI_BORDER_PURPLE}; }}
.kpi-card-red {{ border-top-color: {KPI_BORDER_RED}; }}
.kpi-card-green {{ border-top-color: {KPI_BORDER_GREEN}; }}
.kpi-card-blue {{ border-top-color: {KPI_BORDER_BLUE}; }}

.kpi-label {{
    font-size: 10px;
    font-weight: 500;
    color: {TEXT_SUB};
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}}

.kpi-value {{
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.5px;
    line-height: 1;
    margin-bottom: 4px;
}}

.kpi-desc {{
    font-size: 10px;
    color: {TEXT_SUB};
}}

.kpi-delta {{
    font-size: 10px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 3px;
}}

.kpi-delta.up {{
    background: rgba(76,175,80,0.1);
    color: {SUCCESS};
}}

.kpi-delta.down {{
    background: rgba(244,67,54,0.08);
    color: {DANGER};
}}

/* ═══════════════════════════════════════════════════════════════════════
   RISK BADGES
═══════════════════════════════════════════════════════════════════════ */
.risk-badge {{
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: 700;
    font-size: 11px;
}}

.risk-high {{
    background: {RISK_HIGH_BG};
    color: {RISK_HIGH_TEXT};
}}

.risk-medium {{
    background: {RISK_MEDIUM_BG};
    color: {RISK_MEDIUM_TEXT};
}}

.risk-low {{
    background: {RISK_LOW_BG};
    color: {RISK_LOW_TEXT};
}}

/* ═══════════════════════════════════════════════════════════════════════
   STATUS DOT
═══════════════════════════════════════════════════════════════════════ */
.status-badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    font-weight: 600;
}}

.status-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
}}

.dot-green {{ background: {SUCCESS}; }}
.dot-red {{ background: {DANGER}; }}
.dot-gray {{ background: #9e9e9e; }}
.dot-yellow {{ background: {WARNING}; }}

/* ═══════════════════════════════════════════════════════════════════════
   TABLE STYLES
═══════════════════════════════════════════════════════════════════════ */
.transaction-id {{
    font-family: {FONT_MONO};
    color: {PRIMARY};
    font-size: 11px;
}}

.prob-high {{ color: {DANGER}; font-weight: 600; font-family: {FONT_MONO}; }}
.prob-medium {{ color: #e65100; font-weight: 600; font-family: {FONT_MONO}; }}
.prob-low {{ color: #2e7d32; font-weight: 600; font-family: {FONT_MONO}; }}

/* ═══════════════════════════════════════════════════════════════════════
   SUMMARY BAR
═══════════════════════════════════════════════════════════════════════ */
.summary-bar {{
    background: {PRIMARY_BG};
    border: 1px solid rgba(74,60,140,0.15);
    border-radius: 6px;
    padding: 8px 14px;
    display: flex;
    gap: 20px;
    align-items: center;
    flex-wrap: wrap;
    font-size: 11px;
    color: {PRIMARY};
}}

.summary-item strong {{
    font-weight: 700;
}}

.summary-sep {{
    width: 1px;
    height: 14px;
    background: rgba(74,60,140,0.2);
}}

/* ═══════════════════════════════════════════════════════════════════════
   FILTER BAR
═══════════════════════════════════════════════════════════════════════ */
.filter-bar {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}}

/* ═══════════════════════════════════════════════════════════════════════
   METRIC CARD (Model Performance)
════════════════════════════════════════════════════════════════════════ */
.metric-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {BORDER_RADIUS_CARD};
    padding: 16px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    margin-bottom: 12px;
}}

.metric-label {{
    font-size: 10px;
    font-weight: 600;
    color: {TEXT_SUB};
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}}

.metric-value {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin-bottom: 6px;
}}

.metric-pass {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 3px;
    margin-bottom: 4px;
}}

.metric-pass.pass {{
    background: rgba(76,175,80,0.1);
    color: #2e7d32;
}}

.metric-pass.fail {{
    background: rgba(244,67,54,0.08);
    color: {DANGER};
}}

.metric-target {{
    font-size: 9px;
    color: {TEXT_SUB};
}}

/* ═══════════════════════════════════════════════════════════════════════
   STATUS CARD (API Health)
═══════════════════════════════════════════════════════════════════════ */
.status-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {BORDER_RADIUS_CARD};
    padding: {CARD_PADDING};
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid;
}}

.status-label {{
    font-size: 10px;
    font-weight: 600;
    color: {TEXT_SUB};
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
}}

.status-value {{
    font-size: 13px;
    font-weight: 600;
}}

.status-sub {{
    font-size: 10px;
    color: {TEXT_SUB};
    margin-top: 4px;
}}

/* ═══════════════════════════════════════════════════════════════════════
   ENDPOINT STYLE
═══════════════════════════════════════════════════════════════════════ */
.endpoint {{
    font-family: {FONT_MONO};
    font-size: 10px;
    color: {PRIMARY};
}}

.error-type {{
    font-family: {FONT_MONO};
    font-size: 10px;
    background: rgba(244,67,54,0.08);
    color: {DANGER};
    padding: 1px 6px;
    border-radius: 3px;
}}

/* ═══════════════════════════════════════════════════════════════════════
   CONFUSION MATRIX
═══════════════════════════════════════════════════════════════════════ */
.cm-container {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 8px 0;
}}

.cm-row {{
    display: flex;
    gap: 6px;
}}

.cm-cell {{
    width: 80px;
    height: 72px;
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
}}

.cm-cell .cm-value {{
    font-size: 20px;
    font-weight: 700;
}}

.cm-cell .cm-label {{
    font-size: 9px;
    font-weight: 600;
    opacity: 0.75;
}}

.cm-tp {{ background: #c8e6c9; color: #1b5e20; }}
.cm-fp {{ background: #ffcdd2; color: #b71c1c; }}
.cm-fn {{ background: #ffe0b2; color: #bf360c; }}
.cm-tn {{ background: #e8eaf6; color: #1a237e; }}

/* ═══════════════════════════════════════════════════════════════════════
   EMPTY STATE
═══════════════════════════════════════════════════════════════════════ */
.empty-state {{
    text-align: center;
    padding: 40px 20px;
    color: {TEXT_SUB};
}}

.empty-state-icon {{
    font-size: 32px;
    margin-bottom: 12px;
}}

.empty-state-text {{
    font-size: 13px;
}}

/* ═══════════════════════════════════════════════════════════════════════
   CARD CONTAINER (for wrapping Plotly charts)
═══════════════════════════════════════════════════════════════════════ */
.card-container {{
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    margin-bottom: 12px;
}}

.card-container > div:first-child {{
    margin-bottom: 12px;
}}
</style>
"""


# ═══════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════

PAGE_CONFIG = {
    "page_title": "FraudLens · Fraud Detection Dashboard",
    "page_icon": "🛡️",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}


# ═══════════════════════════════════════════════════════════════════════
# NAVIGATION ITEMS
# ═══════════════════════════════════════════════════════════════════════

NAV_ITEMS = [
    {"page": "dashboard/pages/1_Overview.py", "icon": "🏠", "label": "Overview"},
    {"page": "dashboard/pages/2_Model_Performance.py", "icon": "📊", "label": "Model Performance"},
    {"page": "dashboard/pages/3_Transactions.py", "icon": "🔍", "label": "Transactions"},
    {"page": "dashboard/pages/4_API_Health.py", "icon": "⚕️", "label": "API Health"},
]


# ═══════════════════════════════════════════════════════════════════════
# RISK LEVELS
# ═══════════════════════════════════════════════════════════════════════

RISK_THRESHOLDS = {
    "HIGH": 0.7,
    "MEDIUM": 0.3,
    "LOW": 0.0,
}


def get_risk_level(probability: float) -> str:
    """Get risk level from probability."""
    if probability >= RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    elif probability >= RISK_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    else:
        return "LOW"


def get_risk_badge_html(risk_level: str) -> str:
    """Get HTML for risk badge."""
    colors = {
        "HIGH": {"bg": "rgba(244,67,54,0.1)", "text": "#F44336"},
        "MEDIUM": {"bg": "rgba(255,193,7,0.12)", "text": "#e65100"},
        "LOW": {"bg": "rgba(76,175,80,0.1)", "text": "#2e7d32"},
    }
    color = colors.get(risk_level, colors["LOW"])

    return f'<span style="display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 3px; font-weight: 700; font-size: 11px; background: {color["bg"]}; color: {color["text"]};">{risk_level}</span>'


def get_status_dot_html(status: str) -> str:
    """Get HTML for status dot."""
    color = {
        "healthy": "#4CAF50",
        "online": "#4CAF50",
        "yes": "#4CAF50",
        "unhealthy": "#F44336",
        "offline": "#F44336",
        "no": "#F44336",
        "disabled": "#9e9e9e",
        "warning": "#FFC107",
    }.get(status.lower(), "#9e9e9e")

    return f'<span style="width: 8px; height: 8px; border-radius: 50%; background: {color};"></span>'


# ═══════════════════════════════════════════════════════════════════════
# SHARED STYLES INJECTION
# ═══════════════════════════════════════════════════════════════════════

def inject_shared_styles() -> None:
    """
    Inject shared styles that must be present on every page.

    This hides the native Streamlit navigation and applies global styles.

    MUST be called first thing on every page before any other Streamlit code.
    """
    import streamlit as st

    # Inject custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Hide native Streamlit navigation (not supported in 1.28.1)
    # Fix padding for sidebar and main content
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
        /* Minimal top padding for sidebar */
        [data-testid="stSidebar"] > div {
            padding-top: 0px !important;
        }
        /* Minimal top padding for main content */
        .main .block-container {
            padding-top: 0.5rem !important;
        }
        [data-testid="stAppViewBlockContainer"] {
            padding-top: 25px !important;
        }
        [data-testid="stMainBlockContainer"] {
            padding-top: 25px !important;
        }
        section.main {
            padding-top: 25px !important;
        }
        </style>
    """, unsafe_allow_html=True)


def build_sidebar(current_page: str = "Overview") -> None:
    """
    Build the branded sidebar with navigation and API endpoint config.

    Args:
        current_page: The name of the current page for highlighting (Overview, Model Performance, Transactions, API Health)
    """
    import streamlit as st

    with st.sidebar:
        # Logo
        st.markdown("""
        <div style="padding: 0px 16px 14px; border-bottom: 1px solid #E0E0E0; margin-top: -55px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #4A3C8C; display: grid; place-items: center; font-size: 1rem; color: white;">🛡</div>
                <div>
                    <div style="font-size: 13px; font-weight: 700; color: #4A3C8C;">FraudLens</div>
                    <div style="font-size: 10px; color: #757575;">ML Operations</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation section
        st.markdown("""
        <div style="padding: 8px 8px 4px; font-size: 10px; font-weight: 600; color: #757575; text-transform: uppercase; letter-spacing: 0.08em;">Navigation</div>
        """, unsafe_allow_html=True)

        # Overview
        if current_page == "Overview":
            st.markdown("""
            <div style="padding: 8px 12px; margin-left: 8px; background: #f0f4ff; border-left: 3px solid #4A3C8C; border-radius: 4px; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: 600; color: #4A3C8C;">🏠 Overview</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.page_link("app.py", label="Overview", icon="🏠")

        # Model Performance
        if current_page == "Model Performance":
            st.markdown("""
            <div style="padding: 8px 12px; margin-left: 8px; background: #f0f4ff; border-left: 3px solid #4A3C8C; border-radius: 4px; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: 600; color: #4A3C8C;">📊 Model Performance</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.page_link("pages/1_Model_Performance.py", label="Model Performance", icon="📊")

        # Transactions
        if current_page == "Transactions":
            st.markdown("""
            <div style="padding: 8px 12px; margin-left: 8px; background: #f0f4ff; border-left: 3px solid #4A3C8C; border-radius: 4px; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: 600; color: #4A3C8C;">🔍 Transactions</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.page_link("pages/2_Transactions.py", label="Transactions", icon="🔍")

        # API Health
        if current_page == "API Health":
            st.markdown("""
            <div style="padding: 8px 12px; margin-left: 8px; background: #f0f4ff; border-left: 3px solid #4A3C8C; border-radius: 4px; margin-bottom: 4px;">
                <span style="font-size: 13px; font-weight: 600; color: #4A3C8C;">⚕️ API Health</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.page_link("pages/3_API_Health.py", label="API Health", icon="⚕️")

        # Spacer to push config to bottom
        st.markdown("<div style='flex: 1;'></div>", unsafe_allow_html=True)

        # Config section at bottom
        st.markdown(f"""
        <div style="border-top: 1px solid #E0E0E0; padding: 12px; margin-top: 20px;">
            <div style="font-size: 10px; font-weight: 600; color: #757575; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.07em;">API Endpoint</div>
            <div style="background: #f5f5f5; border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px 8px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #757575; word-break: break-all;">
        {API_BASE_URL}
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 8px;">
                <span style="font-size: 10px;">Auto Refresh</span>
                <span style="font-size: 10px; color: #4A3C8C; background: white; border: 1px solid #E0E0E0; border-radius: 4px; padding: 2px 6px;">30s</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def card_header(title: str, subtitle: str = "") -> str:
    """
    Generate HTML for a card header.

    Args:
        title: Card title
        subtitle: Optional subtitle

    Returns:
        HTML string for the card header
    """
    if subtitle:
        return f"""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 600; color: #333333;">{title}</div>
            <div style="font-size: 11px; color: #757575;">{subtitle}</div>
        </div>
        """
    else:
        return f"""
        <div style="font-size: 13px; font-weight: 600; color: #333333; margin-bottom: 12px;">{title}</div>
        """


def render_chart_card(title: str, subtitle: str, chart_fn, empty_fn=None) -> None:
    """
    Render a chart inside a properly styled card container.

    This function creates a container, applies card styling via CSS,
    and renders the chart inside it.

    Args:
        title: Card title
        subtitle: Card subtitle
        chart_fn: Function that returns the Plotly figure
        empty_fn: Optional function that returns HTML for empty state
    """
    import streamlit as st

    # Inject CSS for this specific card container
    card_id = f"card_{id(title)}"
    st.markdown(f"""
    <style>
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > .plotly) {{
        background: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Render header
    st.markdown(card_header(title, subtitle), unsafe_allow_html=True)

    # Render chart or empty state
    if empty_fn and chart_fn is None:
        st.markdown(empty_fn(), unsafe_allow_html=True)
    else:
        fig = chart_fn()
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
