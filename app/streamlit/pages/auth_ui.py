import time
import streamlit as st
from datetime import datetime

# --- Core utilities ---
from utils.session_utils import (
    logout_user,
    handle_post_logout_redirect,
    ensure_user_session,
    active_session_refresh,
)

from utils.navbar import inject_global_styles, render_navbar, add_navbar_spacer, render_footer

# --- DB functions ---
from guardian_compliance_db import (
    create_user, verify_user, create_session, get_user_by_session,
    create_email_verification_token, verify_email_token,
    create_password_reset_token, reset_password_with_token,
    get_user_id_by_email, db
)

from streamlit_cookies_manager import EncryptedCookieManager


# ============================================================
# 🔐 COOKIE MANAGER (MUST BE SINGLE INSTANCE)
# ============================================================
if "cookies" in st.session_state:
    cookies = st.session_state["cookies"]
else:
    cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
    if not cookies.ready():
        st.stop()
    st.session_state["cookies"] = cookies


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="🔐 Login | Compliance Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

inject_global_styles()
render_navbar(namespace="chat")
add_navbar_spacer()


# ============================================================
# UNIVERSAL SESSION RESTORE
# ============================================================
handle_post_logout_redirect()

# Restore session from cookie → ONLY once
user = ensure_user_session()

# Refresh expiry ONLY if user exists
if user:
    active_session_refresh()

# If already logged in → route to chat
if user:
    st.switch_page("pages/chat.py")
    st.stop()


# ============================================================
# HIDE SIDEBAR ONLY WHEN NOT LOGGED IN
# ============================================================
if not st.session_state.get("user_info"):
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            visibility: hidden !important;
            width: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ============================================================
# INITIALIZE AUTH STATE
# ============================================================
def init_auth_state():
    if "session_token" not in st.session_state:
        st.session_state.session_token = cookies.get("session_token", "")
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    if "auth_page" not in st.session_state:
        st.session_state.auth_page = "login"
    if "verified_flag" not in st.session_state:
        st.session_state.verified_flag = False  # for "verified successfully" message


# ============================================================
# SESSION MANAGEMENT
# ============================================================
def load_user_session():
    token = st.session_state.get("session_token")
    if not token:
        token = cookies.get("session_token", "")
        st.session_state.session_token = token

    if token:
        user = get_user_by_session(token)
        if user:
            st.session_state.user_info = user
            cookies["session_token"] = token
            cookies.save()
            return True
        cookies["session_token"] = ""
        cookies.save()
    return False


# ============================================================
# LOGIN FORM
# ============================================================

def login_form():
    """Login form with verification + resend link handling."""

    # Show registration success message if present
    if st.session_state.get("registration_success"):
        st.success("✅ Account created! Please verify your email before login.")
        del st.session_state["registration_success"]  # clear flash message

  
    cookies = st.session_state["cookies"]
    COOKIE_KEY = "session_token"

    # ✅ If user just verified via email
    if st.session_state.get("verified_flag"):
        st.success("✅ Your email is verified! Please log in now.")
        st.session_state.verified_flag = False

    st.markdown("### 🔐 Login to Compliance Guardian")

    # Input fields
    email = st.text_input("Email", key="login_email", placeholder="you@example.com")
    password = st.text_input("Password", type="password", key="login_password")

    # 🔒 Store last email for later resend use
    if email:
        st.session_state["last_email"] = email.strip().lower()

    # --- LOGIN BUTTON ---
    if st.button("Login", use_container_width=True):
        if not email or not password:
            st.warning("Please enter both email and password.")
            return

        with st.spinner("Verifying credentials..."):
            try:
                user_id = verify_user(email, password)
                if not user_id:
                    st.error("❌ Invalid email or password.")
                    return

                # ✅ Credentials valid — create server-side session token
                token = create_session(user_id)
                st.session_state["session_token"] = token

                # ✅ Save token into encrypted cookie
                try:
                    cookies[COOKIE_KEY] = token
                    cookies.save()       # only once, right here
                except Exception as e:
                    st.warning("⚠️ Cookie manager not ready. Please try again.")
                    print(f"Cookie error: {e}")
                    return

                # ✅ Mark for redirect only after cookie is saved
                st.success("✅ Login successful! Redirecting...")
                st.session_state["redirect_to_chat"] = True
                time.sleep(1)
                st.rerun()

            # --- Handle unverified email case ---
            except PermissionError:
                pending_email = st.session_state.get("last_email", "").strip().lower()
                st.session_state["unverified_email"] = pending_email
                st.warning("⚠️ Email not verified. Please verify or resend the link below.")

            # --- Catch-all error ---
            except Exception as e:
                st.error(f"⚠️ Unexpected error: {e}")
                print(f"⚠️ Login error: {e}")

    # --- RESEND VERIFICATION LINK SECTION ---
    unverified_email = st.session_state.get("unverified_email", "")
    if unverified_email:
        st.info(f"📩 Verification pending for: **{unverified_email}**")

        if st.button("📧 Resend Verification Link", key=f"resend_{unverified_email}"):
            try:
                uid = get_user_id_by_email(unverified_email)
                if uid:
                    with db() as conn:
                        conn.execute("DELETE FROM email_tokens WHERE user_id=?", (uid,))
                        conn.commit()

                    new_token = create_email_verification_token(uid)
                    verify_url = f"http://localhost:8501/auth_ui?verify={new_token}"

                    st.success("✅ A new verification link has been generated!")
                    st.code(verify_url, language="text")
                else:
                    st.error("❌ Could not find this email in our database.")
            except Exception as e:
                st.error(f"❌ Failed to resend verification link: {e}")

    # --- Footer options ---
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧾 Create Account"):
            st.session_state["auth_mode"] = "register"
            st.session_state.pop("auth_page", None)
            st.rerun()

    with col2:
        if st.button("🔑 Forgot Password?"):
            st.session_state["auth_mode"] = "forgot"
            st.session_state.pop("auth_page", None)
            st.rerun()




# ============================================================
# REGISTER FORM
# ============================================================
def register_form():
    st.markdown("### 🧾 Create an Account")
    email = st.text_input("Email", key="reg_email", placeholder="you@example.com")
    name = st.text_input("Name", key="reg_name", placeholder="John Doe")
    password = st.text_input("Password", type="password", key="reg_password")
    confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

    # --- REGISTER BUTTON HANDLER ---
    if st.button("Register", use_container_width=True):
        if not email or not password or not confirm:
            st.warning("Please fill all fields.")
        elif password != confirm:
            st.warning("Passwords do not match.")
        else:
            with st.spinner("Creating your account..."):
                try:
                    # 1️⃣ Create user + async verification email
                    user_id = create_user(email, password, name)
                    if not user_id:
                        st.error("❌ Registration failed. Please try again.")
                        return

                    # 2️⃣ Show temporary success message
                    st.success("✅ Account created! Please verify your email before login.")

                    # 3️⃣ Set session_state flash message for login page
                    st.session_state["registration_success"] = True

                    # 4️⃣ Redirect explicitly to login page
                    st.session_state["auth_mode"] = "login"
                    st.switch_page("pages/auth_ui.py")

                except Exception as e:
                    if "UNIQUE constraint failed" in str(e):
                        st.warning("⚠️ Email already registered. Please log in.")
                    else:
                        st.error(f"❌ Unexpected error: {e}")


# ============================================================
# FORGOT PASSWORD
# ============================================================
def forgot_password_form():
    st.markdown("### 🔑 Forgot Password")
    email = st.text_input("Enter your registered email:")
    if st.button("Send Reset Link"):
        if not email:
            st.warning("Please enter your email.")
        else:
            uid = get_user_id_by_email(email)
            if uid:
                token = create_password_reset_token(uid)
                reset_url = f"http://localhost:8501/auth_ui?reset={token}"
                st.info(f"📧 Reset link (dev mode): {reset_url}")
            else:
                st.error("❌ Email not found.")

    if st.button("⬅ Back to Login"):
        st.session_state["auth_mode"] = "login"
        st.rerun()


# ============================================================
# EMAIL + RESET TOKEN HANDLERS
# ============================================================
def reset_password_form(token: str):
    st.markdown("### 🔒 Reset Password")
    new_pw = st.text_input("New Password", type="password")
    confirm_pw = st.text_input("Confirm Password", type="password")

    if st.button("Reset Password"):
        if not new_pw or not confirm_pw:
            st.warning("Please fill both fields.")
        elif new_pw != confirm_pw:
            st.warning("Passwords do not match.")
        else:
            ok = reset_password_with_token(token, new_pw)
            if ok:
                st.success("✅ Password reset successful! Redirecting...")
                time.sleep(1)
                st.session_state.auth_page = "login"
                st.query_params.clear()
                st.rerun()
            else:
                st.error("❌ Invalid or expired token.")

def verify_email_form(token: str):
    """Handle email verification from link."""
    st.markdown("### 📧 Email Verification")

    try:
        token = token.strip()
        if not token:
            st.error("❌ Missing verification token.")
            return

        if verify_email_token(token):
            # ✅ Mark verified in session for login success message
            st.session_state.verified_flag = True

            st.success("✅ Email verified successfully! Redirecting to login...")
            time.sleep(1.5)

            # Clear query params so ?verify=token disappears
            st.query_params.clear()

            # Force re-render of login form on same page
            st.session_state.auth_page = "login"
            st.rerun()
        else:
            st.error("❌ Invalid or expired verification link.")
    except Exception as e:
        st.error(f"⚠️ Verification failed: {e}")

# ============================================================
#                         AUTH GATE
# ============================================================

def auth_gate():
    """Handles login/register/reset with proper session restore."""
    query = st.query_params

    # Handle verification and password reset tokens
    if "verify" in query:
        verify_email_form(query.get("verify")); return
    if "reset" in query:
        reset_password_form(query.get("reset")); return

    # Route to correct auth screen
    page = st.session_state.get("auth_mode") or st.session_state.get("auth_page", "login")
    if page == "login":
        login_form()
    elif page == "register":
        register_form()
    elif page == "forgot":
        forgot_password_form()
    return False

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__" or True:
    st.title("🔐 Compliance Guardian Authentication")
    # Apply global page + navbar CSS
    # inject_global_styles()
    # # Render the navbar
    # render_navbar(namespace="auth")
    # # Add spacing below navbar so content doesn’t overlap
    # add_navbar_spacer()

    auth_gate()

    render_footer()