from utils.access_control import require_login
import streamlit as st
import time
from guardian_compliance_db import db
from utils.auth_utils import show_user_header
from utils.session_utils import handle_post_logout_redirect

# ============================================================
# 🧭 Page Setup + Auth Header
# ============================================================
st.set_page_config(page_title="📑 Audit Logs — Admin", page_icon="📑", layout="wide")

# Show sidebar header and handle logout redirects
show_user_header()
handle_post_logout_redirect()

# ============================================================
# 🧩 Admin Permission Check
# ============================================================
user = st.session_state.get("user_info")

if not user:
    require_login()

if user.get("role") != "admin":
    st.error("⚠️ Access Denied — Admin permission required to view this page.")
    st.stop()

# ============================================================
# 📑 Audit Logs Content (Admin Only)
# ============================================================
st.title("📑 Audit Logs — Session Activity")

with db() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, event_type, event_data, created_at
        FROM audit_logs
        WHERE event_type LIKE 'session_%' OR event_type = 'user_logout'
        ORDER BY created_at DESC
    """)
    logs = cur.fetchall()

if logs:
    for uid, evt, data, ts in logs:
        st.markdown(f"**👤 User {uid}** — `{evt}`")
        st.json(data)
        st.caption(f"🕓 {ts}")
        st.markdown("---")
else:
    st.info("No session activity recorded yet.")