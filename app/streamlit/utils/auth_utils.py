import streamlit as st
from utils.session_utils import logout_user

def show_user_header():
    """Sidebar with user info + logout button."""
    
    # Reset guard each run
    st.session_state["_header_rendered"] = False

    user = st.session_state.get("user_info")
    if not user:
        return

    with st.sidebar:

        # --- User info ---
        st.markdown(f"### 👤 {user.get('name') or user.get('email')}")
        st.caption(f"Role: `{user.get('role', 'user')}`")

        # --- Admin Links ---
        # if user.get("role") == "admin":
        #     st.markdown("---")
        #     st.markdown("### 🧭 Admin Tools")
        #     st.markdown("- [🛡️ Role Management](app/pages/role_management.py)")
        #     st.markdown("- [📊 Dashboard](app/pages/dashboard_ui.py)")
        #     st.markdown("- [📑 Audit Logs](app/pages/audit_logs.py)")
        #     st.markdown("- [🧾 Policy Logs](app/pages/policy_logs.py)")

        st.markdown("---")

        # --- Unique logout button ---
        token = st.session_state.get("session_token", "anon")
        logout_key = f"sidebar_logout_btn_{token}"

        st.button(
            "🚪 Logout",
            key=logout_key,
            use_container_width=True,
            on_click=logout_user,
            kwargs={"redirect_to": "app.py"},
        )