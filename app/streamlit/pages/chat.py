import os
import requests
from datetime import datetime, timezone
import streamlit as st
from openai import OpenAI
from guardian_compliance_db import (
    fetch_chat_history,
    save_chat_message,
    log_policy_event,
)

from utils.session_utils import (
    ensure_user_session,
    handle_post_logout_redirect,
    active_session_refresh,
)
from utils.auth_utils import show_user_header
from streamlit_cookies_manager import EncryptedCookieManager
import streamlit as st

# FORCE SIDEBAR VISIBLE
st.markdown("""
<style>
[data-testid="stSidebar"] {
    visibility: visible !important;
    width: 260px !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 🔐 LOAD COOKIE MANAGER FIRST (MUST BE FIRST!)
# ============================================================
if "cookies" not in st.session_state:
    cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
    if not cookies.ready():
        st.stop()
    st.session_state["cookies"] = cookies
else:
    cookies = st.session_state["cookies"]

# ============================================================
# 🔐 SESSION LIFECYCLE (Flexible Mode — user optional)
# ============================================================

# 1️⃣ Handle any pending logout redirections
handle_post_logout_redirect()

# 2️⃣ Try to restore user from cookie/session
user = ensure_user_session()

# 3️⃣ Extend session expiry only if user exists
if user:
    active_session_refresh()

# 4️⃣ Safe user_id (None allowed)
user_id = user["id"] if user else None

# 5️⃣ Always render sidebar if user exists
#    If no user → sidebar stays hidden automatically
show_user_header()


# ============================================================
# ⚙️ PAGE CONFIG
# ============================================================
# st.set_page_config(page_title="💬 Compliance Guardian Chat", page_icon="", layout="wide")
st.title("💬 Compliance Guardian Chat")
st.caption("Sensitive-data-aware chat with real-time policy enforcement.")

# ============================================================
# 🧠 API CONFIG
# ============================================================
GUARDIAN_API = os.getenv("GUARDIAN_API", "http://localhost:8000")
LLM_API = os.getenv("LLM_API", "http://localhost:12434/engines/llama.cpp/v1")
MODEL_NAME = "ai/llama3.1:latest"
client = OpenAI(base_url=LLM_API, api_key="not-needed")


# ============================================================
# 💬 CHAT SESSION SETUP
# ============================================================
if "message_count" not in st.session_state:
    st.session_state["message_count"] = 0
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

chat_key = f"messages_{user_id or 'guest'}"
if chat_key not in st.session_state:
    st.session_state[chat_key] = (
        fetch_chat_history(user_id) if user_id else st.session_state["chat_history"]
    )
messages = st.session_state[chat_key]


# ============================================================
# 🧱 DISPLAY CHAT HISTORY
# ============================================================
chat_container = st.container()
with chat_container:
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# ============================================================
# 🚧 GUEST CHAT LIMITS
# ============================================================
if st.session_state.get("redirect_to_auth"):
    st.session_state["redirect_to_auth"] = False
    st.switch_page("pages/auth_ui.py")

if not user_id:
    count = st.session_state.get("message_count", 0)

    # Hard limit — must sign up
    if count >= 15:
        st.error("🔒 Free chat limit reached. Please create an account to continue.")
        if st.button("🔑 Create Account / Login", use_container_width=True):
            st.session_state["auth_mode"] = "login"
            st.session_state["redirect_to_auth"] = True
            st.rerun()
        st.stop()

    # Soft warnings
    elif count in (4, 10):
        st.warning(
            "💬 You’re chatting as a guest. Sign up to save your messages and get unlimited access.",
            icon="⚠️"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Login", use_container_width=True):
                st.session_state["auth_mode"] = "login"
                st.session_state["redirect_to_auth"] = True
                st.rerun()
        with col2:
            if st.button("🆕 Create Account", use_container_width=True):
                st.session_state["auth_mode"] = "register"
                st.session_state["redirect_to_auth"] = True
                st.rerun()

    st.caption(f"Free messages used: {count + 1}/15")

# ============================================================
# 💬 CHAT INPUT
# ============================================================
user_input = st.chat_input("Type your message...")

if user_input:
    # --------------------------------------------------------
    # Handle message count for guests
    # --------------------------------------------------------
    if not user_id:
        st.session_state["message_count"] += 1
        if st.session_state["message_count"] > 15:
            st.error("🔒 Free chat limit reached. Please sign up to continue.")
            st.stop()

    # --------------------------------------------------------
    # Save + display user message
    # --------------------------------------------------------
    messages.append({"role": "user", "content": user_input})
    save_chat_message(user_id, "user", user_input)
    with chat_container:
        with st.chat_message("user"):
            st.markdown(user_input)

    # --------------------------------------------------------
    # Compliance scan
    # --------------------------------------------------------
    with st.spinner("🧠 Scanning for compliance risks..."):
        try:
            resp = requests.post(f"{GUARDIAN_API}/analyze", json={"text": user_input}, timeout=20)
            result = resp.json() if resp.ok else {"action": "allow"}
        except Exception as e:
            st.error(f"Guardian API Error: {e}")
            result = {"action": "allow"}

    action = result.get("action", "allow")
    masked_text = result.get("masked_output", user_input)
    regex_hits = result.get("regex_findings", [])
    pii_entities = result.get("pii_entities", [])
    secret_entities = result.get("secret_entities", [])

    # --------------------------------------------------------
    # Policy enforcement
    # --------------------------------------------------------
    if action == "block":
        reply = "🚫 Message blocked by Compliance Policy."
        st.error(reply)
    else:
        user_to_send = masked_text if action == "mask" else user_input
        if action == "mask":
            st.warning("⚠️ Sensitive data detected — masking before sending to LLM.")

        with st.spinner("🤖 Generating secure response..."):
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": user_to_send}],
                    max_tokens=400,
                )
                reply = completion.choices[0].message.content
            except Exception as e:
                reply = f"⚠️ LLM Error: {e}"

    # --------------------------------------------------------
    # Save + display assistant reply
    # --------------------------------------------------------
    messages.append({"role": "assistant", "content": reply})
    save_chat_message(user_id, "assistant", reply)

    with chat_container:
        with st.chat_message("assistant"):
            st.markdown(reply)

    # --------------------------------------------------------
    # Log compliance event
    # --------------------------------------------------------

    policy_id = "chat_message"  # base ID for chat messages

    # Customize based on action
    if action == "mask":
        policy_id += "_masked"
    elif action == "block":
        policy_id += "_blocked"

    all_findings = []
    if regex_hits:
        all_findings.extend(regex_hits)
    if pii_entities:
        all_findings.extend(pii_entities)
    if secret_entities:  # assuming you have a list of secret/confidential items
        all_findings.extend(secret_entities)

    log_policy_event(
        user_id=user_id,
        policy_id=policy_id,
        action=action,
        findings=all_findings,
        raw_content=user_input
    )
    # --------------------------------------------------------
    # Local log file
    # --------------------------------------------------------
    os.makedirs("chat_logs", exist_ok=True)
    with open("chat_logs/history.jsonl", "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | user={user_id or 'guest'} | {action} | {user_input}\n")

    # --------------------------------------------------------
    # Show Compliance Details
    # --------------------------------------------------------
    with st.expander("🔍 Compliance Analysis Details", expanded=False):
        st.write(f"**Action:** `{action}`")
        if action == "mask":
            st.write(f"**Masked Text:** {masked_text}")
        if regex_hits:
            st.write(f"**Regex Findings:** {regex_hits}")
        if pii_entities:
            st.write(f"**PII Entities:** {pii_entities}")