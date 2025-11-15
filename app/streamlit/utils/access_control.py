import streamlit as st
import time

def is_admin() -> bool:
    """Return True if current logged-in user is an admin."""
    user = st.session_state.get("user_info")
    return bool(user and user.get("role") == "admin")


def require_admin():
    """
    Decorator-style function to protect admin-only pages.
    If a non-admin accesses the page, show an error and stop execution.
    """
    user = st.session_state.get("user_info")

    if not user:
        require_login()

    if user.get("role") != "admin":
        st.error("⚠️ Access denied: Admin privileges required.")
        st.stop()


def require_login():
    """
    Simple login protection for general user pages.
    """
    if "user_info" not in st.session_state or not st.session_state["user_info"]:
        st.warning("🔒 Please log in to access this page.")
        time.sleep(0.4)
        st.switch_page("pages/auth_ui.py")
        st.stop()