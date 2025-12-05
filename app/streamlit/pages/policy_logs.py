import time
from utils.access_control import require_login
import streamlit as st
from utils.auth_utils import show_user_header
from utils.session_utils import ensure_user_session, handle_post_logout_redirect
from guardian_compliance_db import db  # Database access

handle_post_logout_redirect()

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
    # Decode findings JSON safely
    try:
        findings = json.loads(log[4]) if log[4] else []
    except Exception:
        findings = str(log[4])

    # Decode raw_content (may be dict or JSON string)
    raw_val = log[7]
    if raw_val:
        try:
            raw_val = json.loads(raw_val)
        except Exception:
            raw_val = str(raw_val)

    logs_data.append({
        "Event ID": log[0],
        "User ID": str(log[1] or "Guest"),
        "Policy ID": str(log[2]),
        "Action": log[3],
        "Findings": findings[0] if findings else "",
        "IP": str(log[5] or "Unknown"),
        "User Agent": str(log[6] or "Unknown"),
        "User Input": str(raw_val),
        "Created At": pd.to_datetime(log[8], utc=True, errors="coerce")
    })

# Convert to DataFrame safely
if logs_data:
    df = pd.DataFrame(logs_data)

    # 🔧 Arrow-safe cast fixes
    df["Event ID"] = df["Event ID"].astype("Int64")
    df["User ID"] = df["User ID"].astype("string")
    df["Policy ID"] = df["Policy ID"].astype("string")
    df["Action"] = df["Action"].astype("string")
    df["Findings"] = df["Findings"].astype("string")
    df["IP"] = df["IP"].astype("string")
    df["User Agent"] = df["User Agent"].astype("string")
    df["User Input"] = df["User Input"].astype("string")

    # Created At must be datetime64[ns, UTC]
    df["Created At"] = pd.to_datetime(df["Created At"], utc=True, errors="coerce")

    st.dataframe(df)

else:
    st.info("No policy events logged yet.")