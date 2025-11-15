# dashboard_ui.py
# ------------------------------------------------------------
# Streamlit Dashboard for AI-Driven Compliance Guardian
# ------------------------------------------------------------
import streamlit as st
from guardian_compliance_db import (
    fetch_chat_history,
    log_policy_event,
    log_audit,
)

# ------------------------------------------------------------
# HOME DASHBOARD
# ------------------------------------------------------------
def dashboard_home(user):
    """Main dashboard home screen."""
    st.markdown(f"## 👋 Welcome, {user.get('name') or user.get('email') or 'User'}!")
    st.caption("Your AI-Driven Compliance Guardian dashboard")
    st.divider()

    # --------------------------------------------------------
    # Recent Conversations
    # --------------------------------------------------------
    st.markdown("### 💬 Recent Conversations")
    try:
        chats = fetch_chat_history(user["id"], limit=5)
    except Exception as e:
        st.error(f"⚠️ Unable to load chat history: {e}")
        chats = []

    if not chats:
        st.info("No previous chat messages found.")
    else:
        for msg in chats[-5:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            timestamp = msg.get("created_at", "")[:19].replace("T", " ")
            with st.chat_message(role.lower()):
                st.markdown(f"**{role}** ({timestamp})")
                st.markdown(content)

    st.divider()

    # --------------------------------------------------------
    # Quick Actions
    # --------------------------------------------------------
    st.markdown("### ⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💬 Go to Chat", key="btn_new_chat"):
            st.switch_page("pages/chat.py")
    with col2:
        if st.button("📋 View Policy Logs", key="btn_policy_logs"):
            st.session_state["nav_page"] = "Policy Events"
            st.experimental_rerun()
    with col3:
        if st.button("🕵️ View Audit Logs", key="btn_audit_logs"):
            st.session_state["nav_page"] = "Audit Logs"
            st.experimental_rerun()

# ------------------------------------------------------------
# PLACEHOLDER PAGES
# ------------------------------------------------------------
def show_policy_logs(user):
    """Display user policy compliance logs."""
    st.markdown("### 📋 Policy Events")
    st.info("Policy event history will be shown here (coming soon).")

def show_audit_logs(user):
    """Display user audit logs."""
    st.markdown("### 🕵️ Audit Logs")
    st.info("Audit log history will be shown here (coming soon).")

def show_settings(user):
    """User account and settings page."""
    st.markdown("### ⚙️ Account Settings")
    st.text(f"Email: {user.get('email', 'N/A')}")
    st.text(f"Role: {user.get('role', 'user')}")
    st.text("Additional settings coming soon...")

# ------------------------------------------------------------
# ROUTER
# ------------------------------------------------------------
def dashboard_router(user):
    """Simple sidebar navigation for dashboard sections."""
    st.sidebar.markdown("### 🧭 Navigation")
    page = st.sidebar.radio(
        "Go to:",
        ["Home", "Settings"],
        label_visibility="collapsed",
    )

    if page == "Home":
        dashboard_home(user)
    # elif page == "Policy Events":
    #     show_policy_logs(user)
    # elif page == "Audit Logs":
    #     show_audit_logs(user)
    elif page == "Settings":
        show_settings(user)