"""
Central theme + small UI helpers so the app looks like a single
cohesive enterprise product instead of a stack of default Streamlit
widgets. Import `inject_theme()` once at the top of app.py.
"""

import streamlit as st


PRIMARY = "#4F7CFF"
PRIMARY_DARK = "#2F52C7"
BG = "#0E1117"
SURFACE = "#ACAFB4"
SURFACE_2 = "#F4F7FD"
BORDER = "#BABFC9"
TEXT_MUTED = "#FCFCFC"
GOOD = "#015520"
WARN = "#F59E0B"
BAD = "#EF4444"


def inject_theme():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {BG};
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: {SURFACE};
            border-right: 1px solid {BORDER};
        }}

        /* Card container used via st.container(border=True) */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: {SURFACE};
            border: 1px solid {BORDER} !important;
            border-radius: 12px;
        }}

        /* Metrics */
        div[data-testid="stMetric"] {{
            background: {SURFACE_2};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 14px 16px 10px 16px;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {TEXT_MUTED};
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        /* Buttons */
        .stButton > button, .stDownloadButton > button {{
            border-radius: 8px;
            border: 1px solid {BORDER};
            font-weight: 600;
        }}
        .stButton > button[kind="primary"] {{
            background: {PRIMARY};
            border: none;
        }}

        /* Tabs */
        button[data-baseweb="tab"] {{
            font-weight: 600;
        }}

        /* Pipeline stepper pill */
        .lp-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .lp-pill-done {{ background: rgba(34,197,94,0.15); color: {GOOD}; }}
        .lp-pill-active {{ background: rgba(79,124,255,0.18); color: {PRIMARY}; }}
        .lp-pill-todo {{ background: rgba(139,150,165,0.12); color: {TEXT_MUTED}; }}

        .lp-header {{
            padding: 22px 26px;
            border-radius: 14px;
            background: linear-gradient(135deg, {PRIMARY_DARK} 0%, {SURFACE} 100%);
            border: 1px solid {BORDER};
            margin-bottom: 18px;
        }}
        .lp-header h1 {{
            margin: 0;
            font-size: 1.65rem;
        }}
        .lp-header p {{
            margin: 6px 0 0 0;
            color: rgba(255,255,255,0.75);
            font-size: 0.95rem;
        }}

        .lp-badge {{
            display: inline-block;
            padding: 2px 9px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }}
        .lp-badge-live {{ background: rgba(34,197,94,0.18); color: {GOOD}; }}
        .lp-badge-sim {{ background: rgba(245,158,11,0.18); color: {WARN}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="lp-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pipeline_stepper(stages: list[str], current_index: int):
    """Render a horizontal 'done / active / todo' stepper for the pipeline."""
    cols = st.columns(len(stages))

    for i, (col, label) in enumerate(zip(cols, stages)):
        if i < current_index:
            css_class, icon = "lp-pill-done", "✓"
        elif i == current_index:
            css_class, icon = "lp-pill-active", "●"
        else:
            css_class, icon = "lp-pill-todo", "○"

        with col:
            st.markdown(
                f'<span class="lp-pill {css_class}">{icon} {label}</span>',
                unsafe_allow_html=True,
            )


def source_badge(is_live: bool) -> str:
    if is_live:
        return '<span class="lp-badge lp-badge-live">LIVE MEASUREMENT</span>'
    return '<span class="lp-badge lp-badge-sim">ESTIMATED</span>'
