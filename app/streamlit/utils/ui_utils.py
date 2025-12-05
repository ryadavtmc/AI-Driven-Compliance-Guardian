import streamlit as st

def hide_auth_ui_link():
    """Globally hide auth_ui link from sidebar navigation."""
    st.markdown("""
        <style>
        /* Works across all Streamlit versions (as of 2024+) */
        [data-testid="stSidebarNav"] ul li a[href*="auth_ui"] {
            display: none !important;
        }
        [data-testid="stSidebarNav"] ul li a[href*="Authentication"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)