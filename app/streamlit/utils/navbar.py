import streamlit as st

def inject_global_styles():
    """Injects the full CSS (navbar, hero, footer, responsiveness)."""
    st.markdown("""
    <style>
    html, body, .stApp {
      background: radial-gradient(circle at 20% 20%, #111217, #09090c 80%) !important;
      color: #fff !important;
      font-family: 'Inter', sans-serif;
      overflow-x: hidden;
    }
    #MainMenu, header, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] {
      display: none !important;
    }

    /* ===== NAVBAR ===== */
    .navbar {
      position: fixed;
      top: 0; left: 0; right: 0;
      height: 70px;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 3rem;
      background: rgba(15, 15, 17, 0.85);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      backdrop-filter: blur(14px);
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      z-index: 1000;
    }
    .nav-left {
      display: flex; align-items: center; gap: 12px;
    }
    .nav-left img {
      width: 36px; height: 36px; border-radius: 50%;
      filter: drop-shadow(0 0 8px rgba(102,126,234,0.5));
    }
    .nav-left span {
      font-size: 1.2rem; font-weight: 700;
      background: linear-gradient(135deg,#fff,#bdbdbd);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .nav-right { display: flex; align-items: center; gap: 14px; }

    /* ===== BUTTONS ===== */
    .stButton > button {
        border-radius: 12px !important;
        padding: 0.6rem 1.1rem !important;
        font-weight: 600 !important;
        border: none !important;
        color: #fff !important;
        background: linear-gradient(135deg,#667eea,#764ba2) !important;
        box-shadow: 0 6px 22px rgba(118,75,162,.35) !important;
        transition: transform .2s ease, box-shadow .2s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 32px rgba(118,75,162,.5) !important;
    }

    /* ===== FOOTER ===== */
    .footer {
      margin-top: 6vh;
      padding: 1.2rem 0;
      text-align: center;
      color: rgba(255,255,255,0.7);
      border-top: 1px solid rgba(255,255,255,0.1);
      background: rgba(14,14,14,0.9);
      font-size: 0.9rem;
    }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {
      .navbar { flex-direction: column; align-items: flex-start; padding: 1rem 1.5rem; height: auto; }
      .nav-left span { font-size: 1rem; }
      .nav-left img { width: 30px; height: 30px; }
      .nav-right { margin-top: 0.5rem; gap: 8px; flex-wrap: wrap; }
    }
    </style>
    """, unsafe_allow_html=True)


# def render_navbar():
#     """Renders a dynamic navbar that hides Login/Signup when user is logged in."""
#     inject_global_styles()

#     user = st.session_state.get("user_info")
#     # --- Layout
#     col1, col2, col3 = st.columns([3, 6, 2])

#     # --- LEFT SIDE: Logo + Title
#     with col1:
#         st.markdown("""
#         <div class="nav-left">
#           <img src="https://cdn-icons-png.flaticon.com/512/1048/1048941.png">
#           <span>AI-Driven Compliance Guardian</span>
#         </div>
#         """, unsafe_allow_html=True)

#     with col3:
#         if user:
#             # --- Name display ---
#             name = user.get("name") or user.get("email", "User")
#             st.markdown(
#                 f"<div style='text-align:right; font-weight:600;'>👤 {name}</div>",
#                 unsafe_allow_html=True
#             )

#             # --- UNIQUE logout button key ---
#             token = st.session_state.get("session_token", "anon")
#             navbar_logout_key = f"navbar_logout_btn_{token}"

#             if st.button("🚪 Logout", key=navbar_logout_key, use_container_width=True):
#                 from utils.session_utils import logout_user
#                 logout_user("app.py")   # Handles cookie clearing + redirect

#             return  # ⛔ IMPORTANT: prevent the login buttons from rendering

#         else:
#             # --- Login / Signup buttons (only when not logged in) ---
#             c1, c2 = st.columns(2)

#             if c1.button("Log In", key="navbar_login_btn", use_container_width=True):
#                 st.session_state["auth_mode"] = "login"
#                 st.switch_page("pages/auth_ui.py")

#             if c2.button("Sign Up", key="navbar_signup_btn", use_container_width=True):
#                 st.session_state["auth_mode"] = "register"
#                 st.switch_page("pages/auth_ui.py")

def render_navbar(namespace="default"):
    """Renders a dynamic navbar with isolated unique keys per page."""

    inject_global_styles()

    user = st.session_state.get("user_info")

    col1, col2, col3 = st.columns([3, 6, 2])

    # ---- LEFT: LOGO / TITLE ----
    with col1:
        st.markdown("""
        <div class="nav-left">
          <img src="https://cdn-icons-png.flaticon.com/512/1048/1048941.png">
          <span>AI-Driven Compliance Guardian</span>
        </div>
        """, unsafe_allow_html=True)

    # ---- RIGHT: USER OR LOGIN BUTTONS ----
    with col3:

        if user:
            display_name = user.get("name") or user.get("email")

            st.markdown(
                f"<div style='text-align:right; font-weight:600;'>👤 {display_name}</div>",
                unsafe_allow_html=True
            )

            # UNIQUE LOGOUT KEY
            token = st.session_state.get("session_token", "guest")
            logout_key = f"navbar_logout_{namespace}_{token}"

            if st.button("🚪 Logout", key=logout_key, use_container_width=True):
                from utils.session_utils import logout_user
                logout_user("app.py")

        else:
            # UNIQUE LOGIN/SIGNUP KEYS
            login_key = f"navbar_login_btn_{namespace}"
            signup_key = f"navbar_signup_btn_{namespace}"

            c1, c2 = st.columns(2)

            if c1.button("Log In", key=login_key, use_container_width=True):
                st.session_state["auth_mode"] = "login"
                st.switch_page("pages/auth_ui.py")

            if c2.button("Sign Up", key=signup_key, use_container_width=True):
                st.session_state["auth_mode"] = "register"
                st.switch_page("pages/auth_ui.py")

def add_navbar_spacer():
    """Adds vertical spacing below navbar."""
    st.markdown("<div style='height:15vh'></div>", unsafe_allow_html=True)


def render_footer():
    """Render footer identical to the home page."""
    st.markdown("""
    <div class="footer">
      © 2025 AI-Driven Compliance Guardian — Secure. Ethical. Private.
    </div>
    """, unsafe_allow_html=True)