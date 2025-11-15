import time
from utils.access_control import require_login
import streamlit as st
from utils.auth_utils import show_user_header
from utils.session_utils import ensure_user_session, handle_post_logout_redirect
from guardian_compliance_db import db  # Database access

handle_post_logout_redirect()
# from utils.ui_utils import hide_sidebar_on_auth_pages

# Display user header (shows name + logout)
show_user_header()

user = ensure_user_session()

if not user:
    require_login()

if user.get("role") != "admin":
    st.error("⚠️ Access Denied — Admin permission required to view this page.")
    st.stop()


# ============================================================
# POLICY LOGS DISPLAY
# ============================================================
st.title("📜 Policy Logs — Admin View")

import json
import pandas as pd
from guardian_compliance_db import db
import streamlit as st

# Fetch latest 100 policy events
with db() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, policy_id, action, findings, ip_address,
               user_agent, raw_content, created_at
        FROM policy_events
        ORDER BY created_at DESC
        LIMIT 100
    """)
    rows = cur.fetchall()

# Prepare list of dicts for DataFrame
logs_data = []
for log in rows:
    # Safely decode JSON findings
    try:
        findings = json.loads(log[4]) if log[4] else []
    except json.JSONDecodeError:
        findings = []

    logs_data.append({
        "Event ID": log[0],
        "User ID": log[1] or "Guest",
        "Policy ID": log[2],
        "Action": log[3],
        "Findings": findings,
        "IP": log[5] or "Unknown",
        "User Agent": log[6] or "Unknown",
        "Raw Content": log[7] or "",
        "Created At": log[8]
    })

# Display in table
if logs_data:
    df = pd.DataFrame(logs_data)
    st.dataframe(df)
else:
    st.info("No policy events logged yet.")