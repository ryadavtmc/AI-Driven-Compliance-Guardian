# import os
# import requests
# from datetime import datetime, timezone
# import streamlit as st
# from openai import OpenAI
# from guardian_compliance_db import (
#     fetch_chat_history,
#     save_chat_message,
#     log_policy_event,
# )

# from utils.session_utils import (
#     ensure_user_session,
#     handle_post_logout_redirect,
#     active_session_refresh,
# )
# from utils.auth_utils import show_user_header
# from streamlit_cookies_manager import EncryptedCookieManager
# import streamlit as st
# from groq import Groq

# # FORCE SIDEBAR VISIBLE
# st.markdown("""
# <style>
# [data-testid="stSidebar"] {
#     visibility: visible !important;
#     width: 260px !important;
# }
# </style>
# """, unsafe_allow_html=True)


# # ============================================================
# # 🔐 LOAD COOKIE MANAGER FIRST (MUST BE FIRST!)
# # ============================================================
# if "cookies" not in st.session_state:
#     cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
#     if not cookies.ready():
#         st.stop()
#     st.session_state["cookies"] = cookies
# else:
#     cookies = st.session_state["cookies"]

# # ============================================================
# # 🔐 SESSION LIFECYCLE (Flexible Mode — user optional)
# # ============================================================

# # 1️⃣ Handle any pending logout redirections
# handle_post_logout_redirect()

# # 2️⃣ Try to restore user from cookie/session
# user = ensure_user_session()

# # 3️⃣ Extend session expiry only if user exists
# if user:
#     active_session_refresh()

# # 4️⃣ Safe user_id (None allowed)
# user_id = user["id"] if user else None

# # 5️⃣ Always render sidebar if user exists
# #    If no user → sidebar stays hidden automatically
# show_user_header()


# # ============================================================
# # ⚙️ PAGE CONFIG
# # ============================================================
# # st.set_page_config(page_title="💬 Compliance Guardian Chat", page_icon="", layout="wide")
# st.title("💬 Compliance Guardian Chat")
# st.caption("Sensitive-data-aware chat with real-time policy enforcement.")

# # ============================================================
# # 🧠 API CONFIG
# # ============================================================
# # client = Groq()

# GUARDIAN_API = os.getenv("GUARDIAN_API", "http://localhost:8000")
# # LLM_API = os.getenv("LLM_API", "http://localhost:12434/engines/llama.cpp/v1")
# # # MODEL_NAME = "ai/qwen3:latest"
# # client = OpenAI(base_url=LLM_API, api_key="not-needed")


# GROQ_API_KEY = os.getenv("ai-driven-compliance-guardian")
# if not GROQ_API_KEY:
#     st.error("⚠️ Groq API key is missing. Set ai-driven-compliance-guardian in your .env file.")
#     st.stop()

# client = Groq(api_key=GROQ_API_KEY)
# # MODEL_NAME = "llama-3.3-70b-versatile"
# MODEL_NAME = "openai/gpt-oss-20b"

# # Example usage:
# # completion = client.chat(model=MODEL_NAME, messages=[{"role": "user", "content": user_input}])


# # ============================================================
# # 💬 CHAT SESSION SETUP
# # ============================================================
# if "message_count" not in st.session_state:
#     st.session_state["message_count"] = 0
# if "chat_history" not in st.session_state:
#     st.session_state["chat_history"] = []

# chat_key = f"messages_{user_id or 'guest'}"
# if chat_key not in st.session_state:
#     st.session_state[chat_key] = (
#         fetch_chat_history(user_id) if user_id else st.session_state["chat_history"]
#     )
# messages = st.session_state[chat_key]


# ###########################################################
# # Before sending to LLM
# ############################################################

# messages_to_send = st.session_state[chat_key]

# # Optional: truncate to last N messages or summarise older context
# MAX_HISTORY = 20
# messages_to_send = [
#     {"role": m["role"], "content": m["content"]}
#     for m in messages[-MAX_HISTORY:]
# ]


# # ============================================================
# # 🧱 DISPLAY CHAT HISTORY
# # ============================================================
# chat_container = st.container()
# with chat_container:
#     for msg in messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])


# # ============================================================
# # 🚧 GUEST CHAT LIMITS
# # ============================================================
# if st.session_state.get("redirect_to_auth"):
#     st.session_state["redirect_to_auth"] = False
#     st.switch_page("pages/auth_ui.py")

# if not user_id:
#     count = st.session_state.get("message_count", 0)

#     # Hard limit — must sign up
#     if count >= 15:
#         st.error("🔒 Free chat limit reached. Please create an account to continue.")
#         if st.button("🔑 Create Account / Login", use_container_width=True):
#             st.session_state["auth_mode"] = "login"
#             st.session_state["redirect_to_auth"] = True
#             st.rerun()
#         st.stop()

#     # Soft warnings
#     elif count in (4, 10):
#         st.warning(
#             "💬 You’re chatting as a guest. Sign up to save your messages and get unlimited access.",
#             icon="⚠️"
#         )
#         col1, col2 = st.columns(2)
#         with col1:
#             if st.button("🔑 Login", use_container_width=True):
#                 st.session_state["auth_mode"] = "login"
#                 st.session_state["redirect_to_auth"] = True
#                 st.rerun()
#         with col2:
#             if st.button("🆕 Create Account", use_container_width=True):
#                 st.session_state["auth_mode"] = "register"
#                 st.session_state["redirect_to_auth"] = True
#                 st.rerun()

#     st.caption(f"Free messages used: {count + 1}/15")

# # ============================================================
# # 💬 CHAT INPUT
# # ============================================================
# user_input = st.chat_input("Type your message...")

# if user_input:
#     # --------------------------------------------------------
#     # Handle message count for guests
#     # --------------------------------------------------------
#     if not user_id:
#         st.session_state["message_count"] += 1
#         if st.session_state["message_count"] > 15:
#             st.error("🔒 Free chat limit reached. Please sign up to continue.")
#             st.stop()

#     # --------------------------------------------------------
#     # Save + display user message
#     # --------------------------------------------------------
#     messages.append({"role": "user", "content": user_input})
#     save_chat_message(user_id, "user", user_input)
#     with chat_container:
#         with st.chat_message("user"):
#             st.markdown(user_input)

#     # --------------------------------------------------------
#     # Compliance scan
#     # --------------------------------------------------------
#     with st.spinner("🧠 Scanning for compliance risks..."):
#         try:
#             resp = requests.post(f"{GUARDIAN_API}/analyze", json={"text": user_input}, timeout=20)
#             result = resp.json() if resp.ok else {"action": "allow"}
#         except Exception as e:
#             st.error(f"Guardian API Error: {e}")
#             result = {"action": "allow"}

#     action = result.get("action", "allow")
#     masked_text = result.get("masked_output", user_input)
#     regex_hits = result.get("regex_findings", [])
#     pii_entities = result.get("pii_entities", [])
#     secret_entities = result.get("secret_entities", [])

#     # --------------------------------------------------------
#     # Policy enforcement
#     # --------------------------------------------------------
#     if action == "block":
#         reply = "🚫 Message blocked by Compliance Policy."
#         st.error(reply)
#     else:
#         user_to_send = masked_text if action == "mask" else user_input
#         if action == "mask":
#             st.warning("⚠️ Sensitive data detected — masking before sending to LLM.")

#         with st.spinner("🤖 Generating secure response..."):
#             try:
#                 completion = client.chat.completions.create(
#                     model=MODEL_NAME,
#                     messages=[{"role": "user", "content": user_to_send}],
#                     max_tokens=400,
#                 )
#                 reply = completion.choices[0].message.content
#             except Exception as e:
#                 reply = f"⚠️ LLM Error: {e}"

#     # --------------------------------------------------------
#     # Save + display assistant reply
#     # --------------------------------------------------------

#     # Append assistant reply to session
#     messages.append({"role": "assistant", "content": reply})

#     # Update session state and save both user input and assistant response
#     st.session_state[chat_key] = messages
#     save_chat_message(user_id, "user", user_input)
#     save_chat_message(user_id, "assistant", reply)

#     # messages.append({"role": "user", "content": user_input})
#     # messages.append({"role": "assistant", "content": reply})
#     # st.session_state[chat_key] = messages
#     # save_chat_message(user_id, "user", user_input)
#     # save_chat_message(user_id, "assistant", reply)

#     with chat_container:
#         with st.chat_message("assistant"):
#             st.markdown(reply)

#     # --------------------------------------------------------
#     # Log compliance event
#     # --------------------------------------------------------

#     policy_id = "chat_message"  # base ID for chat messages

#     # Customize based on action
#     if action == "mask":
#         policy_id += "_masked"
#     elif action == "block":
#         policy_id += "_blocked"

#     all_findings = []
#     if regex_hits:
#         all_findings.extend(regex_hits)
#     if pii_entities:
#         all_findings.extend(pii_entities)
#     if secret_entities:  # assuming you have a list of secret/confidential items
#         all_findings.extend(secret_entities)

#     log_policy_event(
#         user_id=user_id,
#         policy_id=policy_id,
#         action=action,
#         findings=all_findings,
#         raw_content=user_input
#     )
#     # --------------------------------------------------------
#     # Local log file
#     # --------------------------------------------------------
#     os.makedirs("chat_logs", exist_ok=True)
#     with open("chat_logs/history.jsonl", "a") as f:
#         f.write(f"{datetime.now(timezone.utc).isoformat()} | user={user_id or 'guest'} | {action} | {user_input}\n")

#     # --------------------------------------------------------
#     # Show Compliance Details
#     # --------------------------------------------------------
#     with st.expander("🔍 Compliance Analysis Details", expanded=False):
#         st.write(f"**Action:** `{action}`")
#         if action == "mask":
#             st.write(f"**Masked Text:** {masked_text}")
#         if regex_hits:
#             st.write(f"**Findings:** {regex_hits}")
#         if pii_entities:
#             st.write(f"**PII Entities:** {pii_entities}")




# import os
# import requests
# from datetime import datetime, timezone
# import streamlit as st
# from groq import Groq
# from guardian_compliance_db import fetch_chat_history, save_chat_message, log_policy_event
# from utils.session_utils import ensure_user_session, handle_post_logout_redirect, active_session_refresh
# from utils.auth_utils import show_user_header
# from streamlit_cookies_manager import EncryptedCookieManager

# # -----------------------------
# # Streamlit sidebar visibility
# # -----------------------------
# st.markdown("""
# <style>
# [data-testid="stSidebar"] {
#     visibility: visible !important;
#     width: 260px !important;
# }
# </style>
# """, unsafe_allow_html=True)

# # =========================
# # COOKIE / SESSION SETUP
# # =========================
# if "cookies" not in st.session_state:
#     cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
#     if not cookies.ready():
#         st.stop()
#     st.session_state["cookies"] = cookies
# else:
#     cookies = st.session_state["cookies"]

# handle_post_logout_redirect()
# user = ensure_user_session()
# if user:
#     active_session_refresh()
# user_id = user["id"] if user else None
# show_user_header()

# # =========================
# # PAGE CONFIG
# # =========================
# st.title("💬 Compliance Guardian Chat")
# st.caption("Sensitive-data-aware chat with real-time policy enforcement.")

# # =========================
# # API & LLM CONFIG
# # =========================
# GUARDIAN_API = os.getenv("GUARDIAN_API", "http://localhost:8000")
# GROQ_API_KEY = os.getenv("ai-driven-compliance-guardian")
# if not GROQ_API_KEY:
#     st.error("⚠️ Groq API key is missing. Set ai-driven-compliance-guardian in your .env file.")
#     st.stop()
# client = Groq(api_key=GROQ_API_KEY)
# MODEL_NAME = "openai/gpt-oss-20b"

# # =========================
# # CHAT SESSION
# # =========================
# if "message_count" not in st.session_state:
#     st.session_state["message_count"] = 0
# if "chat_history" not in st.session_state:
#     st.session_state["chat_history"] = []

# chat_key = f"messages_{user_id or 'guest'}"
# if chat_key not in st.session_state:
#     st.session_state[chat_key] = fetch_chat_history(user_id) if user_id else []

# messages = st.session_state[chat_key]

# # =========================
# # DISPLAY CHAT HISTORY
# # =========================
# chat_container = st.container()
# with chat_container:
#     for msg in messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

# # =========================
# # GUEST CHAT LIMITS
# # =========================
# if st.session_state.get("redirect_to_auth"):
#     st.session_state["redirect_to_auth"] = False
#     st.switch_page("pages/auth_ui.py")

# if not user_id:
#     count = st.session_state.get("message_count", 1)
#     if count >= 15:
#         st.error("🔒 Free chat limit reached. Please create an account to continue.")
#         if st.button("🔑 Create Account / Login", use_container_width=True):
#             st.session_state["auth_mode"] = "login"
#             st.session_state["redirect_to_auth"] = True
#             st.rerun()
#         st.stop()
#     elif count in (4, 10):
#         st.warning(
#             "💬 You’re chatting as a guest. Sign up to save your messages and get unlimited access.",
#             icon="⚠️"
#         )
#     st.caption(f"Free messages used: {count}/15")

# # =========================
# # CHAT INPUT
# # =========================
# user_input = st.chat_input("Type your message...")
# if user_input:
#     if not user_id:
#         st.session_state["message_count"] += 1
#         if st.session_state["message_count"] > 15:
#             st.error("🔒 Free chat limit reached. Please sign up to continue.")
#             st.stop()

#     # Append user input to history
#     messages.append({"role": "user", "content": user_input})
#     save_chat_message(user_id, "user", user_input)

#     # Compliance scan
#     with st.spinner("🧠 Scanning for compliance risks..."):
#         try:
#             resp = requests.post(f"{GUARDIAN_API}/analyze", json={"text": user_input}, timeout=20)
#             result = resp.json() if resp.ok else {"action": "allow"}
#         except Exception as e:
#             st.error(f"Guardian API Error: {e}")
#             result = {"action": "allow"}

#     action = result.get("action", "allow")
#     masked_text = result.get("masked_output", user_input)
#     regex_hits = result.get("regex_findings", [])
#     pii_entities = result.get("pii_entities", [])
#     secret_entities = result.get("secret_entities", [])

#     # Policy enforcement
#     if action == "block":
#         reply = "🚫 Message blocked by Compliance Policy."
#         st.error(reply)
#     else:
#         user_to_send = masked_text if action == "mask" else user_input
#         if action == "mask":
#             st.warning("⚠️ Sensitive data detected — masking before sending to LLM.")

#         # Prepare messages for LLM (truncate & remove unsupported fields)
#         MAX_HISTORY = 20
#         # messages_to_send = [
#         #     {"role": m["role"], "content": m["content"]}
#         #     for m in messages[-MAX_HISTORY:]
#         # ]

#         messages_to_send = []

#         for m in messages[-MAX_HISTORY:]:
#             text = m["content"]

#             # Re-run compliance scan on every message
#             try:
#                 resp = requests.post(f"{GUARDIAN_API}/analyze", json={"text": text}, timeout=10)
#                 r = resp.json() if resp.ok else {"action": "allow"}
#             except:
#                 r = {"action": "allow"}

#             if r.get("action") == "block":
#                 safe_text = "[BLOCKED FOR POLICY REASONS]"
#             elif r.get("action") == "mask":
#                 safe_text = r.get("masked_output", "[MASKED]")
#             else:
#                 safe_text = text

#             messages_to_send.append({
#                 "role": m["role"],
#                 "content": safe_text
#             })

#         # Generate LLM response
#         with st.spinner("🤖 Generating secure response..."):
#             try:
#                 completion = client.chat.completions.create(
#                     model=MODEL_NAME,
#                     messages=messages_to_send,
#                     max_tokens=400
#                 )
#                 reply = completion.choices[0].message.content
#             except Exception as e:
#                 reply = f"⚠️ LLM Error: {e}"

#     # Append assistant reply
#     messages.append({"role": "assistant", "content": reply})

#     # Update session & database
#     st.session_state[chat_key] = messages
#     save_chat_message(user_id, "assistant", reply)

#     with chat_container:
#         with st.chat_message("assistant"):
#             st.markdown(reply)

#     # Log compliance event
#     policy_id = "chat_message"
#     if action == "mask":
#         policy_id += "_masked"
#     elif action == "block":
#         policy_id += "_blocked"

#     all_findings = []
#     all_findings.extend(regex_hits)
#     all_findings.extend(pii_entities)
#     all_findings.extend(secret_entities)

#     log_policy_event(
#         user_id=user_id,
#         policy_id=policy_id,
#         action=action,
#         findings=all_findings,
#         raw_content=user_input
#     )

#     # Local log file
#     os.makedirs("chat_logs", exist_ok=True)
#     with open("chat_logs/history.jsonl", "a") as f:
#         f.write(f"{datetime.now(timezone.utc).isoformat()} | user={user_id or 'guest'} | {action} | {user_input}\n")

#     # Show Compliance Details
#     with st.expander("🔍 Compliance Analysis Details", expanded=False):
#         st.write(f"**Action:** `{action}`")
#         if action == "mask":
#             st.write(f"**Masked Text:** {masked_text}")
#         if regex_hits:
#             st.write(f"**Findings:** {regex_hits}")
#         if pii_entities:
#             st.write(f"**PII Entities:** {pii_entities}")










# import os
# import requests
# from datetime import datetime, timezone, timedelta
# import streamlit as st
# from groq import Groq
# from guardian_compliance_db import fetch_chat_history, save_chat_message, log_policy_event
# from utils.session_utils import ensure_user_session, handle_post_logout_redirect, active_session_refresh
# from utils.auth_utils import show_user_header
# from streamlit_cookies_manager import EncryptedCookieManager

# # =========================
# # CONSTANTS
# # =========================
# HISTORY_DAYS = 15               # show last N days only (UI + display filter)
# GUEST_MESSAGE_LIMIT = 15        # free guest messages
# MAX_HISTORY = 20                # context turns sent to LLM
# EXCLUDE_ASSISTANT_FROM_CONTEXT = False  # set True to never include assistant messages

# # -----------------------------
# # Streamlit sidebar visibility
# # -----------------------------
# st.markdown("""
# <style>
# [data-testid="stSidebar"] {
#     visibility: visible !important;
#     width: 260px !important;
# }
# </style>
# """, unsafe_allow_html=True)

# # =========================
# # COOKIE / SESSION SETUP
# # =========================
# if "cookies" not in st.session_state:
#     cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
#     if not cookies.ready():
#         st.stop()
#     st.session_state["cookies"] = cookies
# else:
#     cookies = st.session_state["cookies"]

# handle_post_logout_redirect()
# user = ensure_user_session()
# if user:
#     active_session_refresh()
# user_id = user["id"] if user else None
# show_user_header()

# # =========================
# # PAGE CONFIG
# # =========================
# st.title("💬 Compliance Guardian Chat")
# st.caption("Sensitive-data-aware chat with real-time policy enforcement.")
# # st.caption(f"⏱️ History window: last {HISTORY_DAYS} days (older messages hidden).")

# # =========================
# # API & LLM CONFIG
# # =========================
# GUARDIAN_API = os.getenv("GUARDIAN_API", "http://localhost:8000")
# # Keep original env var name used in your project; fall back to GROQ_API_KEY if present
# GROQ_API_KEY = os.getenv("ai-driven-compliance-guardian") or os.getenv("GROQ_API_KEY")
# if not GROQ_API_KEY:
#     st.error("⚠️ Groq API key is missing. Set ai-driven-compliance-guardian (or GROQ_API_KEY) in your .env file.")
#     st.stop()
# client = Groq(api_key=GROQ_API_KEY)
# MODEL_NAME = "openai/gpt-oss-20b"

# # =========================
# # STATE
# # =========================
# if "message_count" not in st.session_state:
#     st.session_state["message_count"] = 0
# if "chat_history" not in st.session_state:
#     st.session_state["chat_history"] = []

# chat_key = f"messages_{user_id or 'guest'}"
# if chat_key not in st.session_state:
#     st.session_state[chat_key] = fetch_chat_history(user_id) if user_id else []

# # =========================
# # HELPERS
# # =========================
# def _parse_dt(val):
#     if not val:
#         return None
#     try:
#         if isinstance(val, (int, float)):
#             return datetime.fromtimestamp(val, tz=timezone.utc)
#         if isinstance(val, datetime):
#             return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
#         return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
#     except Exception:
#         return None

# def filter_messages_last_n_days(msgs, days=HISTORY_DAYS):
#     """Filter display to last N days, normalizing timestamps safely."""
#     if not msgs:
#         return msgs

#     cutoff = datetime.now(timezone.utc) - timedelta(days=days)
#     filtered = []

#     for m in msgs:
#         ts = None

#         # Check for supported timestamp keys
#         for k in ("created_at", "timestamp", "ts"):
#             if k in m:
#                 ts = _parse_dt(m.get(k))
#                 break

#         # If timestamp is missing or unparsable -> keep message
#         if ts is None:
#             filtered.append(m)
#             continue

#         # -----------------------------
#         # FIX: Normalize timezone here
#         # -----------------------------
#         if ts.tzinfo is None:
#             ts = ts.replace(tzinfo=timezone.utc)

#         # Now comparison is safe
#         if ts >= cutoff:
#             filtered.append(m)

#     return filtered

# def analyze_text(text: str, timeout=20):
#     try:
#         resp = requests.post(f"{GUARDIAN_API}/analyze", json={"text": text}, timeout=timeout)
#         return resp.json() if resp.ok else {"action": "allow"}
#     except Exception as e:
#         st.error(f"Guardian API Error: {e}")
#         return {"action": "allow"}

# def safe_store_text(action: str, user_text: str, masked_text: str | None):
#     if action == "block":
#         return "[BLOCKED BY POLICY]"
#     if action == "mask":
#         return masked_text or "[MASKED]"
#     return user_text

# def safe_log_text(action: str, user_text: str, masked_text: str | None):
#     if action == "block":
#         return "[BLOCKED BY POLICY]"
#     if action == "mask":
#         return masked_text or "[MASKED]"
#     return user_text

# def sanitize_history_for_llm(history, max_turns=MAX_HISTORY):
#     """Defense-in-depth: re-scan each message before sending to LLM."""
#     to_send = []
#     for m in history[-max_turns:]:
#         if EXCLUDE_ASSISTANT_FROM_CONTEXT and m.get("role") == "assistant":
#             continue
#         text = m.get("content", "")
#         r = analyze_text(text, timeout=10)
#         if r.get("action") == "block":
#             safe_text = "[BLOCKED FOR POLICY REASONS]"
#         elif r.get("action") == "mask":
#             # safe_text = r.get("masked_output", "[MASKED]")
#             masked = r.get("masked_output")
#             # If the analyzer didn't provide a masked_output (or it's empty),
#             # fall back to the current text (which is already sanitized in storage).
#             safe_text = masked if masked not in (None, "") else text
#         else:
#             safe_text = text
#         to_send.append({"role": m.get("role", "user"), "content": safe_text})
#     return to_send

# # =========================
# # HISTORY (DISPLAY) + BANNER
# # =========================
# messages_all = st.session_state[chat_key]
# messages = filter_messages_last_n_days(messages_all, HISTORY_DAYS)
# # show banner
# # st.info(f"🗓️ Showing chat messages from the last **{HISTORY_DAYS} days**. Older messages are hidden.", icon="🗓️")

# # =========================
# # DISPLAY CHAT HISTORY
# # =========================
# chat_container = st.container()
# with chat_container:
#     for msg in messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

# # =========================
# # GUEST CHAT LIMITS
# # =========================
# if st.session_state.get("redirect_to_auth"):
#     st.session_state["redirect_to_auth"] = False
#     st.switch_page("pages/auth_ui.py")

# if not user_id:
#     count = st.session_state.get("message_count", 0)
#     if count >= GUEST_MESSAGE_LIMIT:
#         st.error("🔒 Free chat limit reached. Please create an account to continue.")
#         if st.button("🔑 Create Account / Login", use_container_width=True):
#             st.session_state["auth_mode"] = "login"
#             st.session_state["redirect_to_auth"] = True
#             st.rerun()
#         st.stop()
#     elif count in (4, 10):
#         st.warning(
#             f"💬 You’re chatting as a guest. Limit: {GUEST_MESSAGE_LIMIT} messages. "
#             f"History visible for the last {HISTORY_DAYS} days. "
#             "Sign up to save history and get unlimited access.",
#             icon="⚠️"
#         )
#     st.caption(f"Free messages used: {count}/{GUEST_MESSAGE_LIMIT}")

# # =========================
# # CHAT INPUT
# # =========================
# user_input = st.chat_input("Type your message...")
# if user_input:
#     # 0) Guest message counting
#     if not user_id:
#         st.session_state["message_count"] += 1
#         if st.session_state["message_count"] > GUEST_MESSAGE_LIMIT:
#             st.error("🔒 Free chat limit reached. Please sign up to continue.")
#             st.stop()

#     # 1) COMPLIANCE SCAN FIRST (before storing/logging/calling LLM)
#     with st.spinner("🧠 Scanning for compliance risks..."):
#         result = analyze_text(user_input, timeout=20)

#     action = result.get("action", "allow")
#     masked_text = result.get("masked_output", None)
#     regex_hits = result.get("regex_findings", [])
#     pii_entities = result.get("pii_entities", [])
#     secret_entities = result.get("secret_entities", [])

#     # 2) Sanitize the text for storage & display
#     stored_user_text = safe_store_text(action, user_input, masked_text)

#     # 3) Append sanitized user message (NEVER raw)
#     # Note: If your DB schema has timestamp columns, add them here.
#     messages.append({"role": "user", "content": stored_user_text})
#     save_chat_message(user_id, "user", stored_user_text)

#     # 4) If blocked → DO NOT call LLM
#     if action == "block":
#         reply = "🚫 Message blocked by Compliance Policy."
#         st.error(reply)
#     else:
#         if action == "mask":
#             st.warning("⚠️ Sensitive data detected — masking before sending to LLM.")

#         # 5) Build SAFE context for LLM (re-scanned)
#         messages_to_send = sanitize_history_for_llm(messages, max_turns=MAX_HISTORY)

#         # Prepend a system instruction for masked tokens
#         messages_to_send.insert(0, {
#             "role": "system",
#             "content": (
#                 "You may see placeholders like [REDACTED_EMAIL] or [REDACTED_PII]. "
#                 "Those indicate sensitive data that was removed. Proceed normally using "
#                 "the remaining context to answer the user's request."
#             )
#         })

#         # 6) Call LLM with sanitized history only
#         with st.spinner("🤖 Generating secure response..."):
#             try:
#                 completion = client.chat.completions.create(
#                     model=MODEL_NAME,
#                     messages=messages_to_send,
#                     max_tokens=400
#                 )
#                 reply = completion.choices[0].message.content
#             except Exception as e:
#                 reply = f"⚠️ LLM Error: {e}"

#     # 7) Append assistant reply
#     messages.append({"role": "assistant", "content": reply})

#     # 8) Update session & database (store assistant as-is; if you prefer, you can sanitize too)
#     st.session_state[chat_key] = messages
#     save_chat_message(user_id, "assistant", reply)

#     # 9) Render assistant reply
#     with chat_container:
#         with st.chat_message("assistant"):
#             st.markdown(reply)

#     # 10) Log compliance event (sanitized)
#     policy_id = "chat_message"
#     if action == "mask":
#         policy_id += "_masked"
#     elif action == "block":
#         policy_id += "_blocked"

#     all_findings = []
#     all_findings.extend(regex_hits or [])
#     all_findings.extend(pii_entities or [])
#     all_findings.extend(secret_entities or [])

#     log_policy_event(
#         user_id=user_id,
#         policy_id=policy_id,
#         action=action,
#         findings=all_findings,
#         raw_content=safe_log_text(action, user_input, masked_text)  # never raw
#     )

#     # 11) Local log file (sanitized, never raw)
#     os.makedirs("chat_logs", exist_ok=True)
#     safe_log_line = safe_log_text(action, user_input, masked_text)
#     with open("chat_logs/history.jsonl", "a") as f:
#         f.write(f"{datetime.now(timezone.utc).isoformat()} | user={user_id or 'guest'} | {action} | {safe_log_line}\n")

#     # 12) Show Compliance Details
#     with st.expander("🔍 Compliance Analysis Details", expanded=False):
#         st.write(f"**Action:** `{action}`")
#         if action == "mask" and masked_text:
#             st.write(f"**Masked Text:** {masked_text}")
#         if regex_hits:
#             st.write(f"**Findings:** {regex_hits}")
#         if pii_entities:
#             st.write(f"**PII Entities:** {pii_entities}")


import os
import re  # <-- added
import requests
from datetime import datetime, timezone, timedelta
import streamlit as st
from groq import Groq
from guardian_compliance_db import fetch_chat_history, save_chat_message, log_policy_event
from utils.session_utils import ensure_user_session, handle_post_logout_redirect, active_session_refresh
from utils.auth_utils import show_user_header
from streamlit_cookies_manager import EncryptedCookieManager

# =========================
# CONSTANTS
# =========================
HISTORY_DAYS = 15               # show last N days only (UI + display filter)
GUEST_MESSAGE_LIMIT = 15        # free guest messages
MAX_HISTORY = 20                # context turns sent to LLM
EXCLUDE_ASSISTANT_FROM_CONTEXT = False  # set True to never include assistant messages

# -----------------------------
# Streamlit sidebar visibility
# -----------------------------
st.markdown("""
<style>
[data-testid="stSidebar"] {
    visibility: visible !important;
    width: 260px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# COOKIE / SESSION SETUP
# =========================
if "cookies" not in st.session_state:
    cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
    if not cookies.ready():
        st.stop()
    st.session_state["cookies"] = cookies
else:
    cookies = st.session_state["cookies"]

handle_post_logout_redirect()
user = ensure_user_session()
if user:
    active_session_refresh()
user_id = user["id"] if user else None
show_user_header()

# =========================
# PAGE CONFIG
# =========================
st.title("💬 Compliance Guardian Chat")
st.caption("Sensitive-data-aware chat with real-time policy enforcement.")
# st.caption(f"⏱️ History window: last {HISTORY_DAYS} days (older messages hidden).")

# =========================
# API & LLM CONFIG
# =========================
GUARDIAN_API = os.getenv("GUARDIAN_API", "http://localhost:8000")
# Keep original env var name used in your project; fall back to GROQ_API_KEY if present
GROQ_API_KEY = os.getenv("ai-driven-compliance-guardian") or os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("⚠️ Groq API key is missing. Set ai-driven-compliance-guardian (or GROQ_API_KEY) in your .env file.")
    st.stop()
client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "openai/gpt-oss-20b"

# =========================
# STATE
# =========================
if "message_count" not in st.session_state:
    st.session_state["message_count"] = 0
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

chat_key = f"messages_{user_id or 'guest'}"
if chat_key not in st.session_state:
    st.session_state[chat_key] = fetch_chat_history(user_id) if user_id else []

# =========================
# HELPERS
# =========================
def _parse_dt(val):
    if not val:
        return None
    try:
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(val, tz=timezone.utc)
        if isinstance(val, datetime):
            return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None

def filter_messages_last_n_days(msgs, days=HISTORY_DAYS):
    """Filter display to last N days, normalizing timestamps safely."""
    if not msgs:
        return msgs

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = []

    for m in msgs:
        ts = None

        # Check for supported timestamp keys
        for k in ("created_at", "timestamp", "ts"):
            if k in m:
                ts = _parse_dt(m.get(k))
                break

        # If timestamp is missing or unparsable -> keep message
        if ts is None:
            filtered.append(m)
            continue

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        if ts >= cutoff:
            filtered.append(m)

    return filtered

def analyze_text(text: str, timeout=20):
    try:
        resp = requests.post(f"{GUARDIAN_API}/analyze", json={"text": text}, timeout=timeout)
        return resp.json() if resp.ok else {"action": "allow"}
    except Exception as e:
        st.error(f"Guardian API Error: {e}")
        return {"action": "allow"}

def safe_store_text(action: str, user_text: str, masked_text: str | None):
    if action == "block":
        return "[BLOCKED BY POLICY]"
    if action == "mask":
        return masked_text or "[MASKED]"
    return user_text

def safe_log_text(action: str, user_text: str, masked_text: str | None):
    if action == "block":
        return "[BLOCKED BY POLICY]"
    if action == "mask":
        return masked_text or "[MASKED]"
    return user_text

# ---------- EMAIL NORMALIZATION (fix) ----------
EMAIL_RE = re.compile(r'(?i)\b[a-z0-9._%+\-]+@(?:[a-z0-9\-]+\.)+[a-z]{2,}\b')
BROKEN_EMAIL_REDACTION_RE = re.compile(
    r'\[REDACTED_[A-Z]+\]\s*@\s*[a-z0-9\-]+\s*\.\s*\[REDACTED_[A-Z]+\]', flags=re.I
)
def normalize_masked_email(text: str):
    """Collapse any real or broken/partial masked emails into a single safe token."""
    if not text:
        return text
    # Fix broken patterns like [REDACTED_EMAIL]@gmail.[REDACTED_PII]
    text = BROKEN_EMAIL_REDACTION_RE.sub('[EMAIL_REDACTED]', text)
    # Replace any real/remaining emails
    text = EMAIL_RE.sub('[EMAIL_REDACTED]', text)
    return text
# ---------------------------------------------

def sanitize_history_for_llm(history, max_turns=MAX_HISTORY):
    """Defense-in-depth: re-scan each message before sending to LLM."""
    to_send = []
    for m in history[-max_turns:]:
        if EXCLUDE_ASSISTANT_FROM_CONTEXT and m.get("role") == "assistant":
            continue
        text = m.get("content", "")
        r = analyze_text(text, timeout=10)
        if r.get("action") == "block":
            safe_text = "[BLOCKED FOR POLICY REASONS]"
        elif r.get("action") == "mask":
            masked = r.get("masked_output")
            # Prefer analyzer's masked_output; otherwise keep current (already sanitized in storage)
            safe_text = masked if masked not in (None, "") else text
            # FIX: normalize any email fragments into a single token
            safe_text = normalize_masked_email(safe_text)
        else:
            safe_text = text
        to_send.append({"role": m.get("role", "user"), "content": safe_text})
    return to_send

# =========================
# HISTORY (DISPLAY) + BANNER
# =========================
messages_all = st.session_state[chat_key]
messages = filter_messages_last_n_days(messages_all, HISTORY_DAYS)
# show banner
# st.info(f"🗓️ Showing chat messages from the last **{HISTORY_DAYS} days**. Older messages are hidden.", icon="🗓️")

# =========================
# DISPLAY CHAT HISTORY
# =========================
chat_container = st.container()
with chat_container:
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# =========================
# GUEST CHAT LIMITS
# =========================
if st.session_state.get("redirect_to_auth"):
    st.session_state["redirect_to_auth"] = False
    st.switch_page("pages/auth_ui.py")

if not user_id:
    count = st.session_state.get("message_count", 0)
    if count >= GUEST_MESSAGE_LIMIT:
        st.error("🔒 Free chat limit reached. Please create an account to continue.")
        if st.button("🔑 Create Account / Login", use_container_width=True):
            st.session_state["auth_mode"] = "login"
            st.session_state["redirect_to_auth"] = True
            st.rerun()
        st.stop()
    elif count in (4, 10):
        st.warning(
            f"💬 You’re chatting as a guest. Limit: {GUEST_MESSAGE_LIMIT} messages. "
            f"History visible for the last {HISTORY_DAYS} days. "
            "Sign up to save history and get unlimited access.",
            icon="⚠️"
        )
    st.caption(f"Free messages used: {count}/{GUEST_MESSAGE_LIMIT}")

# =========================
# CHAT INPUT
# =========================
user_input = st.chat_input("Type your message...")
if user_input:
    # 0) Guest message counting
    if not user_id:
        st.session_state["message_count"] += 1
        if st.session_state["message_count"] > GUEST_MESSAGE_LIMIT:
            st.error("🔒 Free chat limit reached. Please sign up to continue.")
            st.stop()

    # 1) COMPLIANCE SCAN FIRST (before storing/logging/calling LLM)
    with st.spinner("🧠 Scanning for compliance risks..."):
        result = analyze_text(user_input, timeout=20)

    action = result.get("action", "allow")
    masked_text = result.get("masked_output", None)
    regex_hits = result.get("regex_findings", [])
    pii_entities = result.get("pii_entities", [])
    secret_entities = result.get("secret_entities", [])

    # 2) Sanitize the text for storage & display
    stored_user_text = safe_store_text(action, user_input, masked_text)
    # FIX: normalize any email fragments before storing/displaying
    stored_user_text = normalize_masked_email(stored_user_text)

    # 3) Append sanitized user message (NEVER raw)
    messages.append({"role": "user", "content": stored_user_text})
    save_chat_message(user_id, "user", user_input)

    # 4) If blocked → DO NOT call LLM
    if action == "block":
        reply = "🚫 Message blocked by Compliance Policy."
        st.error(reply)
    else:
        if action == "mask":
            st.warning("⚠️ Sensitive data detected — masking before sending to LLM.")

        # 5) Build SAFE context for LLM (re-scanned)
        messages_to_send = sanitize_history_for_llm(messages, max_turns=MAX_HISTORY)

        # Prepend a system instruction for masked tokens
        messages_to_send.insert(0, {
            "role": "system",
            "content": (
                "You may see placeholders like [EMAIL_REDACTED] or [REDACTED_PII]. "
                "Those indicate sensitive data that was removed. Proceed normally using "
                "the remaining context to answer the user's request."
            )
        })

        # (Optional, extra safety) Normalize all payload texts once more
        for m in messages_to_send:
            m["content"] = normalize_masked_email(m["content"])

        # 6) Call LLM with sanitized history only
        with st.spinner("🤖 Generating secure response..."):
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages_to_send,
                    max_tokens=400
                )
                reply = completion.choices[0].message.content
            except Exception as e:
                reply = f"⚠️ LLM Error: {e}"

    # 7) Append assistant reply
    messages.append({"role": "assistant", "content": reply})

    # 8) Update session & database (store assistant as-is; if you prefer, you can sanitize too)
    st.session_state[chat_key] = messages
    save_chat_message(user_id, "assistant", reply)

    # 9) Render assistant reply
    with chat_container:
        with st.chat_message("assistant"):
            st.markdown(reply)

    # 10) Log compliance event (sanitized)
    policy_id = "chat_message"
    if action == "mask":
        policy_id += "_masked"
    elif action == "block":
        policy_id += "_blocked"

    all_findings = []
    all_findings.extend(regex_hits or [])
    all_findings.extend(pii_entities or [])
    all_findings.extend(secret_entities or [])

    log_policy_event(
        user_id=user_id,
        policy_id=policy_id,
        action=action,
        findings=all_findings,
        raw_content=safe_log_text(action, user_input, masked_text)  # never raw
    )

    # 11) Local log file (sanitized, never raw)
    os.makedirs("chat_logs", exist_ok=True)
    safe_log_line = safe_log_text(action, user_input, masked_text)
    with open("chat_logs/history.jsonl", "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | user={user_id or 'guest'} | {action} | {safe_log_line}\n")

    # 12) Show Compliance Details
    with st.expander("🔍 Compliance Analysis Details", expanded=False):
        st.write(f"**Action:** `{action}`")
        if action == "mask" and masked_text:
            st.write(f"**Masked Text:** {masked_text}")
        if regex_hits:
            st.write(f"**Findings:** {regex_hits}")
        if pii_entities:
            st.write(f"**PII Entities:** {pii_entities}")