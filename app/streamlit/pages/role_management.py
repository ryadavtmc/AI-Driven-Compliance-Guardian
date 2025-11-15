# app/pages/2_🛡️_Role_Management.py

import streamlit as st
from guardian_compliance_db import get_all_users, update_user_role, delete_user
from utils.access_control import require_admin
from utils.access_control import require_admin
from guardian_compliance_db import get_all_users, update_user_role, delete_user

from utils.session_utils import handle_post_logout_redirect
handle_post_logout_redirect()

st.title("🧑‍💼 Role Management Panel")

# ✅ Protect page
require_admin()

st.success("✅ Admin access granted.")

# Fetch and display users
users = get_all_users()
st.dataframe(users)
# --- Require admin authentication ---
require_admin()

st.set_page_config(page_title="🛡️ Role Management", page_icon="🧑‍💼", layout="wide")
st.title("🛡️ Role Management Panel")
st.caption("Manage user roles and access levels for Compliance Guardian.")

# --- Load all users ---
users = get_all_users()

if not users:
    st.info("No registered users found.")
    st.stop()

# --- Display in a data table with actions ---
st.markdown("### 👥 Registered Users")

for user in users:
    col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
    with col1:
        st.markdown(f"**{user['name']}**")
        st.caption(f"📧 {user['email']}")
    with col2:
        st.text(f"🆔 {user['id']}")
    with col3:
        st.text(f"🎭 Role: {user['role']}")
    with col4:
        if user["role"] == "user":
            if st.button("⬆️ Promote to Admin", key=f"promote_{user['id']}"):
                update_user_role(user["id"], "admin")
                st.success(f"✅ {user['name']} promoted to admin!")
                st.rerun()
        elif user["role"] == "admin":
            if st.button("⬇️ Demote to User", key=f"demote_{user['id']}"):
                update_user_role(user["id"], "user")
                st.warning(f"🔄 {user['name']} demoted to user.")
                st.rerun()
    with col5:
        if st.button("🗑️ Delete", key=f"delete_{user['id']}"):
            delete_user(user["id"])
            st.error(f"❌ {user['name']} deleted.")
            st.rerun()

st.success("✅ Role Management Panel loaded successfully.")