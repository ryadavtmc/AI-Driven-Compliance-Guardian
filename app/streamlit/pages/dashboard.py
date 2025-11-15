# app/pages/2_📊_Dashboard.py

from utils.access_control import require_login
import streamlit as st
import time
from dashboard_ui import dashboard_router
from utils.auth_utils import show_user_header
from utils.session_utils import handle_post_logout_redirect
handle_post_logout_redirect()
# ============================================================
# 🧩 PAGE CONFIGURATION
# ============================================================
st.set_page_config(page_title="📊 Compliance Dashboard", page_icon="📈", layout="wide")

# ============================================================
# 🧑 USER HEADER + SESSION CHECK
# ============================================================
show_user_header()

# Retrieve logged-in user from session
user = st.session_state.get("user_info")

if not user:
    # Not logged in → redirect to login
    require_login()

# ============================================================
# 🏠 DASHBOARD ROUTER
# ============================================================
st.title("📊 Compliance Dashboard")

# Route to the appropriate dashboard view
dashboard_router(user)

# ============================================================
# 🧭 HOME SECTION (safe fallback)
# ============================================================
def dashboard_home(user):
    """Dashboard landing section with user greeting and quick stats."""
    if not user:
        st.warning("⚠️ You are not logged in. Please log in to access the dashboard.")
        st.stop()

    st.markdown(f"## 👋 Welcome, {user.get('name') or user.get('email') or 'User'}!")
    st.caption(f"Role: **{user.get('role', 'user')}**")