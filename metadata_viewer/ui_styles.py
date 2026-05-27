"""Streamlit layout CSS for metadata viewer."""

from __future__ import annotations

import streamlit as st

APP_CSS = """
<style>
/* Let user drag sidebar wider — no max-width cap */
section[data-testid="stSidebar"] {
    min-width: 20rem !important;
}
section[data-testid="stSidebar"] > div {
    padding-right: 0.5rem;
}

/* Use full main width (Streamlit default cap is ~46rem) */
[data-testid="stAppViewContainer"] .main .block-container,
[data-testid="stMain"] .block-container {
    max-width: 100% !important;
    width: 100% !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
}

/* Center canvas block; prevent horizontal overflow clipping controls */
[data-testid="stAppViewContainer"] [data-testid="stMain"] {
    overflow-x: auto !important;
}

div[class*="st-key-canvas_wrap"] {
    display: flex;
    justify-content: center;
    width: 100%;
    overflow-x: auto;
}

div[class*="st-key-label_panel"] button p {
    white-space: normal !important;
}

div[class*="st-key-thumb_list"] button p {
    white-space: normal !important;
    font-size: 0.78rem !important;
    text-align: left !important;
}
</style>
"""


def inject_app_styles() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
