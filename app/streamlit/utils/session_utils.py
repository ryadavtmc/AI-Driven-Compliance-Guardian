# # # import streamlit as st
# # # import time
# # # from streamlit_cookies_manager import EncryptedCookieManager


# # # def logout_user(redirect_to: str = "app.py"):
# # #     """
# # #     Safely log out any user:
# # #       • Clears Streamlit session keys
# # #       • Resets cookies
# # #       • Redirects to a specified page (default: app.py)
# # #     Works from anywhere — sidebar, navbar, dashboard, etc.
# # #     """

# # #     # ✅ Clear cookies
# # #     cookies = st.session_state.get("cookies")
# # #     if not cookies:
# # #         cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
# # #         if cookies.ready():
# # #             st.session_state["cookies"] = cookies
# # #     if cookies:
# # #         cookies["session_token"] = ""
# # #         cookies.save()

# # #     # ✅ Clear authentication & user session
# # #     for key in list(st.session_state.keys()):
# # #         if key.startswith(("session", "user", "messages", "auth_")):
# # #             del st.session_state[key]

# # #     # ✅ Mark for redirect
# # #     st.session_state["redirect_after_logout"] = True

# # #     # ✅ Give user feedback
# # #     st.toast("✅ Logged out successfully!", icon="✅")

# # #     # Short delay so toast appears before rerun
# # #     time.sleep(0.5)

# # #     # ✅ Trigger rerun (so redirect will fire cleanly)
# # #     st.rerun()


# # # def handle_post_logout_redirect():
# # #     """
# # #     Must be called early in auth_gate() or main page scripts.
# # #     Checks if logout just happened and redirects appropriately.
# # #     """
# # #     if st.session_state.get("redirect_after_logout"):
# # #         del st.session_state["redirect_after_logout"]
# # #         st.switch_page("app.py")


# # # app/utils/session_utils.py
# # # import time
# # # import streamlit as st
# # # from streamlit_cookies_manager import EncryptedCookieManager

# # # COOKIE_PREFIX = "guardian_"
# # # COOKIE_KEY = "session_token"

# # # def _get_cookies() -> EncryptedCookieManager:
# # #     cookies = st.session_state.get("cookies")
# # #     if not cookies:
# # #         cookies = EncryptedCookieManager(prefix=COOKIE_PREFIX, password="super-secret-key")
# # #         if not cookies.ready():
# # #             # First run may need one rerun for cookies to initialize
# # #             st.stop()
# # #         st.session_state["cookies"] = cookies
# # #     return cookies

# # # def logout_user(redirect_to: str = "app.py"):
# # #     """
# # #     Universal logout:
# # #       • clears cookie session_token
# # #       • clears relevant session_state keys
# # #       • redirects to landing (default: app.py)
# # #     """
# # #     cookies = _get_cookies()
# # #     cookies[COOKIE_KEY] = ""
# # #     cookies.save()

# # #     # Drop only auth/chat related keys (safer than clear())
# # #     for k in list(st.session_state.keys()):
# # #         if k.startswith(("session", "user", "auth_", "messages")) or k in {
# # #             "user_info", "session_token", "redirect_to_chat", "unverified_email",
# # #             "last_email", "verified_flag", "auth_mode", "auth_page"
# # #         }:
# # #             del st.session_state[k]

# # #     # Flag so pages that rerun before switch_page can still redirect
# # #     st.session_state["_redirect_after_logout"] = True

# # #     # Try immediate redirect; if Streamlit blocks it this run, the handler below will do it.
# # #     try:
# # #         st.switch_page(redirect_to)
# # #     except Exception:
# # #         # If called inside widgets/containers that can’t switch immediately
# # #         time.sleep(0.1)
# # #         st.rerun()

# # # def handle_post_logout_redirect(default_target: str = "app.py"):
# # #     """Call this at the top of every page (chat, dashboard, auth_ui, etc.)."""
# # #     if st.session_state.get("_redirect_after_logout"):
# # #         del st.session_state["_redirect_after_logout"]
# # #         st.switch_page(default_target)












# # # app/utils/session_utils.py
# # import time
# # from datetime import datetime
# # import streamlit as st
# # from streamlit_cookies_manager import EncryptedCookieManager
# # from guardian_compliance_db import get_user_by_session, log_audit



# # COOKIE_PREFIX = "guardian_"
# # COOKIE_KEY = "session_token"


# # def _get_cookies() -> EncryptedCookieManager:
# #     # cookies = st.session_state.get("cookies")
# #     # if not cookies:
# #     #     cookies = EncryptedCookieManager(prefix=COOKIE_PREFIX, password="super-secret-key")
# #     #     if not cookies.ready():
# #     #         st.stop()
# #     #     st.session_state["cookies"] = cookies
# #     # return cookies


# #     if "cookies" not in st.session_state:
# #         cookies = EncryptedCookieManager(
# #             prefix=COOKIE_PREFIX,
# #             password="super-secret-key",
# #             key="guardian_cookie_manager",  # ✅ same consistent key
# #         )
# #         if not cookies.ready():
# #             st.stop()
# #         cookies.save()
# #         st.session_state["cookies"] = cookies
# #     else:
# #         cookies = st.session_state["cookies"]

# # def active_session_refresh():
# #     """Refresh session expiry timestamp (keep user logged in for 8 hours)."""
# #     token = st.session_state.get("session_token")
# #     if not token:
# #         return

# #     try:
# #         from guardian_compliance_db import refresh_session_expiry
# #         refresh_session_expiry(token, hours=8)
# #     except Exception as e:
# #         print(f"⚠️ Session refresh failed: {e}")


# # def load_user_session():
# #     """Safely restore session without clearing cookies on refresh."""
# #     # --- Initialize cookies only once ---
# #     if "cookies" not in st.session_state:
# #         cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
# #         if not cookies.ready():
# #             st.stop()
# #         cookies.save()
# #         st.session_state["cookies"] = cookies
# #     else:
# #         cookies = st.session_state["cookies"]

# #     # --- Retrieve token from session_state or cookie ---
# #     token = st.session_state.get("session_token") or cookies.get("session_token", "")
# #     if not token:
# #         return False  # no session found

# #     # --- Validate token in DB ---
# #     user = get_user_by_session(token)

# #     if user:
# #         # ✅ Keep everything synced
# #         st.session_state["session_token"] = token
# #         st.session_state["user_info"] = user
# #         cookies["session_token"] = token
# #         cookies.save()
# #         return True

# #     # ⚠️ DO NOT clear cookies — may cause logout loop on refresh
# #     return False


# # def logout_user(redirect_to="app.py"):
# #     """Universal logout — clear session, cookie, and trigger redirect."""
# #     cookies = _get_cookies()
# #     token = st.session_state.get("session_token")
# #     user = st.session_state.get("user_info")

# #     # --- Optional: Log audit event ---
# #     if user:
# #         try:
# #             log_audit(user["id"], "user_logout", {"timestamp": datetime.utcnow().isoformat()})
# #         except Exception:
# #             pass  # don't block logout if logging fails

# #     # --- Clear cookie ---
# #     cookies[COOKIE_KEY] = ""
# #     cookies.save()

# #     # --- Clear session keys safely ---
# #     keys_to_clear = [
# #         k for k in st.session_state.keys()
# #         if k.startswith(("session", "user", "auth_", "messages"))
# #         or k in {"user_info", "redirect_to_chat", "verified_flag", "auth_mode", "auth_page"}
# #     ]
# #     for k in keys_to_clear:
# #         del st.session_state[k]

# #     # --- Trigger post-logout redirect ---
# #     st.session_state["_logout_triggered"] = redirect_to
# #     st.rerun()


# # def handle_post_logout_redirect():
# #     """
# #     Handles redirection immediately after logout.
# #     Should be called at the top of every page.
# #     """
# #     target = st.session_state.pop("_logout_triggered", None)
# #     if not target:
# #         return  # nothing to do

# #     # ✅ Show confirmation before redirect
# #     st.success("✅ You’ve been logged out successfully. Redirecting...")
# #     time.sleep(0.6)

# #     # --- Try Streamlit's native redirect ---
# #     try:
# #         st.switch_page(target)
# #     except Exception:
# #         # --- HTML meta redirect fallback ---
# #         if target.startswith("pages/"):
# #             target = target.split("pages/")[-1]
# #         st.markdown(
# #             f"""
# #             <meta http-equiv="refresh" content="0; url=/{target}" />
# #             """,
# #             unsafe_allow_html=True,
# #         )
# #         st.stop()

# # def ensure_user_session():
# #     """
# #     Ensures user session is restored from cookies across reloads.
# #     Returns (user, cookies)
# #     """
# #     # ✅ Initialize cookie manager if missing
# #     if "cookies" not in st.session_state:
# #         cookies = EncryptedCookieManager(prefix=COOKIE_PREFIX, password="super-secret-key")
# #         if not cookies.ready():
# #             st.stop()
# #         cookies.save()
# #         st.session_state["cookies"] = cookies
# #     else:
# #         cookies = st.session_state["cookies"]

# #     # ✅ Restore user info from cookie if missing in memory
# #     if "user_info" not in st.session_state or not st.session_state["user_info"]:
# #         token = cookies.get(COOKIE_KEY, "")
# #         if token:
# #             user = get_user_by_session(token)
# #             if user:
# #                 st.session_state["session_token"] = token
# #                 st.session_state["user_info"] = user
# #                 cookies[COOKIE_KEY] = token
# #                 cookies.save()
# #                 return user, cookies
# #         # If invalid token, clear stale cookie
# #         cookies[COOKIE_KEY] = ""
# #         cookies.save()
# #         st.session_state["user_info"] = None
# #         st.session_state["session_token"] = ""

# #     return st.session_state.get("user_info"), cookies





# # app/utils/session_utils.py
# import time
# from datetime import datetime
# import streamlit as st
# from streamlit_cookies_manager import EncryptedCookieManager
# from guardian_compliance_db import get_user_by_session, log_audit

# COOKIE_PREFIX = "guardian_"
# COOKIE_KEY = "session_token"








# def _get_cookies() -> EncryptedCookieManager:
#     """Initialize cookie manager; skip JS bridge if blocked."""
#     if "cookies" in st.session_state:
#         return st.session_state["cookies"]

#     cookies = EncryptedCookieManager(prefix=COOKIE_PREFIX, password="super-secret-key")
#     try:
#         if not cookies.ready():
#             raise RuntimeError("Cookies not ready (browser restriction)")
#     except Exception:
#         # Fallback: emulate cookies in memory
#         class DummyCookies(dict):
#             def save(self): pass
#             def ready(self): return True
#         cookies = DummyCookies()

#     st.session_state["cookies"] = cookies
#     return cookies


# def ensure_user_session():
#     """Persistent server-side sessions — survives reloads."""
#     cookies = _get_cookies()
#     token = st.session_state.get("session_token") or cookies.get(COOKIE_KEY, "")

#     if not token:
#         # Try restoring from Streamlit memory cache
#         token = st.session_state.get("_last_valid_token", "")
#     if not token:
#         return None, cookies

#     user = get_user_by_session(token)
#     if user:
#         st.session_state["user_info"] = user
#         st.session_state["session_token"] = token
#         st.session_state["_last_valid_token"] = token
#         cookies[COOKIE_KEY] = token
#         try:
#             cookies.save()
#         except Exception:
#             pass  # ignore cookie bridge errors
#         return user, cookies

#     return None, cookies



# # def _get_cookies() -> EncryptedCookieManager:
# #     """Safely initialize or return the global cookie manager (no logout on refresh)."""
# #     # If already in session_state, reuse
# #     if "cookies" in st.session_state:
# #         return st.session_state["cookies"]

# #     # Initialize once globally
# #     cookies = EncryptedCookieManager(
# #         prefix=COOKIE_PREFIX,
# #         password="super-secret-key",
# #     )

# #     # ⚙️ Wait for cookies to be ready (avoid early stop)
# #     if not cookies.ready():
# #         st.info("🔄 Restoring your session...")
# #         st.session_state["cookies_loading"] = True
# #         st.stop()  # stops only first rerun, not destructive

# #     # ✅ Save once, stable across reruns
# #     cookies.save()
# #     st.session_state["cookies"] = cookies
# #     return cookies


# # def _get_cookies() -> EncryptedCookieManager:
# #     """Safely reuse cookies across reruns (no logout on refresh)."""
# #     if "cookies" not in st.session_state:
# #         cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
# #         if not cookies.ready():
# #             st.stop()
# #         cookies.save()
# #         st.session_state["cookies"] = cookies
# #     return st.session_state["cookies"]



# # def _get_cookies() -> EncryptedCookieManager:
# #     """
# #     Initialize or reuse EncryptedCookieManager safely.
# #     Falls back to in-memory cookies if browser cookie bridge fails.
# #     """
# #     if "cookies" not in st.session_state:
# #         st.session_state["cookies"] = EncryptedCookieManager(
# #             prefix=COOKIE_PREFIX,
# #             password="super-secret-key",
# #         )
# #         st.session_state["_cookies_bootstrap_attempts"] = 0

# #     cookies = st.session_state["cookies"]

# #     # Wait for browser sync
# #     if not cookies.ready():
# #         attempts = st.session_state.get("_cookies_bootstrap_attempts", 0)

# #         if attempts < 5:
# #             st.session_state["_cookies_bootstrap_attempts"] = attempts + 1
# #             st.info(f"🔄 Initializing secure session... (attempt {attempts + 1}/5)")
# #             time.sleep(0.5)
# #             st.rerun()
# #         else:
# #             st.warning("⚠️ Browser cookie bridge not responding. Using local session fallback.")
# #             # ✅ Fallback: dummy cookie handler in memory
# #             class DummyCookies(dict):
# #                 def save(self): pass
# #                 def ready(self): return True
# #             cookies = DummyCookies()
# #             st.session_state["cookies"] = cookies
# #             return cookies

# #     # Once ready, reset attempts
# #     st.session_state["_cookies_bootstrap_attempts"] = 0
# #     return cookies


# # def ensure_user_session():
# #     """Restores a valid user session without reinitializing cookies."""
# #     cookies = _get_cookies()
# #     token = st.session_state.get("session_token") or cookies.get(COOKIE_KEY, "")
# #     if not token:
# #         return None, cookies

# #     user = get_user_by_session(token)
# #     if user:
# #         st.session_state["user_info"] = user
# #         st.session_state["session_token"] = token
# #         cookies[COOKIE_KEY] = token
# #         cookies.save()
# #         return user, cookies
# #     return None, cookies


# # def ensure_user_session():
# #     """
# #     Restore a valid user session without reinitializing cookies or forcing logout on refresh.

# #     ✅ Keeps cookies persistent across reruns.
# #     ✅ Never clears cookies automatically.
# #     ✅ Gracefully handles transient DB delays.
# #     ✅ Keeps Streamlit and browser tokens in sync.
# #     """
# #     cookies = _get_cookies()

# #     # Retrieve token from memory or cookie
# #     token = st.session_state.get("session_token") or cookies.get(COOKIE_KEY, "")
# #     if not token:
# #         time.sleep(0.3)
# #         token = cookies.get(COOKIE_KEY, "")
# #         if not token:
# #             return None, cookies 

# #     # Try to revalidate against DB (soft failure safe)
# #     try:
# #         user = get_user_by_session(token)
# #     except Exception as e:
# #         print(f"⚠️ DB lookup failed (non-fatal): {e}")
# #         user = None

# #     # ✅ If valid user, sync everything
# #     if user:
# #         st.session_state["user_info"] = user
# #         st.session_state["session_token"] = token
# #         cookies[COOKIE_KEY] = token
# #         cookies.save()
# #         return user, cookies

# #     # ⚠️ If DB temporarily returns None, keep prior valid state
# #     previous_user = st.session_state.get("user_info")
# #     if previous_user and st.session_state.get("session_token") == token:
# #         print("ℹ️ Preserving existing session (transient DB issue).")
# #         return previous_user, cookies

# #     # 💤 Otherwise, treat as guest but keep cookie intact
# #     st.session_state.setdefault("session_token", token)
# #     st.session_state["user_info"] = None
# #     return None, cookies

# # def ensure_user_session():
# #     """
# #     Restore a valid user session once cookies are ready.
# #     Prevents logout when refreshing before cookies are synced.
# #     """
# #     cookies = _get_cookies()

# #     # Case 1: still waiting for cookies to load
# #     if st.session_state.get("waiting_for_cookie"):
# #         del st.session_state["waiting_for_cookie"]
# #         st.info("🔄 Initializing session...")
# #         st.stop()

# #     # Case 2: normal session restore
# #     token = st.session_state.get("session_token") or cookies.get(COOKIE_KEY, "")
# #     if not token:
# #         # 👇 Only skip once, not logout immediately
# #         st.session_state.setdefault("retry_session_check", 0)
# #         st.session_state["retry_session_check"] += 1

# #         if st.session_state["retry_session_check"] <= 1:
# #             st.info("🕓 Loading your session, please wait...")
# #             st.stop()  # one retry cycle
# #         return None, cookies

# #     # Case 3: Try restoring valid user
# #     try:
# #         user = get_user_by_session(token)
# #     except Exception as e:
# #         print(f"⚠️ DB lookup failed (non-fatal): {e}")
# #         user = None

# #     if user:
# #         st.session_state["user_info"] = user
# #         st.session_state["session_token"] = token
# #         cookies[COOKIE_KEY] = token
# #         cookies.save()
# #         st.session_state.pop("retry_session_check", None)
# #         return user, cookies

# #     # Case 4: keep previous user if DB temporarily returns None
# #     previous_user = st.session_state.get("user_info")
# #     if previous_user and st.session_state.get("session_token") == token:
# #         print("ℹ️ Preserving existing session (transient DB issue).")
# #         return previous_user, cookies

# #     st.session_state["user_info"] = None
# #     return None, cookies







# # def ensure_user_session():
# #     """
# #     Restore a valid user session without reinitializing cookies or forcing logout on refresh.

# #     ✅ Keeps cookies persistent across reruns.
# #     ✅ Never clears cookies automatically.
# #     ✅ Gracefully handles DB delays and browser reloads.
# #     """
# #     cookies = _get_cookies()

# #     # --- Retrieve token ---
# #     token = st.session_state.get("session_token") or cookies.get(COOKIE_KEY, "")

# #     # 🩹 Patch: persist token locally so reloads don't lose it even if cookies fail once
# #     if token and "session_token" not in st.session_state:
# #         st.session_state["session_token"] = token

# #     if not token:
# #         return None, cookies

# #     # --- Try loading user from DB ---
# #     try:
# #         user = get_user_by_session(token)
# #     except Exception as e:
# #         print(f"⚠️ DB lookup failed (non-fatal): {e}")
# #         user = None

# #     # --- Valid user ---
# #     if user:
# #         st.session_state["user_info"] = user
# #         cookies[COOKIE_KEY] = token
# #         cookies.save()
# #         return user, cookies

# #     # --- Fallback: if previous user exists, keep session alive temporarily ---
# #     if st.session_state.get("user_info"):
# #         print("ℹ️ Keeping previous user session (possibly transient DB delay).")
# #         return st.session_state["user_info"], cookies

# #     # --- Otherwise, guest mode ---
# #     return None, cookies



def active_session_refresh():
    """Extend session validity by 8 hours if active."""
    token = st.session_state.get("session_token")
    if not token:
        return
    try:
        from guardian_compliance_db import refresh_session_expiry
        refresh_session_expiry(token, hours=8)
    except Exception:
        pass


# # def logout_user(redirect_to="app.py"):
# #     """Logout safely and redirect."""
# #     cookies = _get_cookies()
# #     user = st.session_state.get("user_info")
# #     token = st.session_state.get("session_token")

# #     if user:
# #         try:
# #             log_audit(user["id"], "user_logout", {"timestamp": datetime.utcnow().isoformat()})
# #         except Exception:
# #             pass

# #     cookies[COOKIE_KEY] = ""
# #     cookies.save()

# #     for k in list(st.session_state.keys()):
# #         if k.startswith(("session", "user", "auth_", "messages")) or k in {
# #             "user_info", "auth_mode", "auth_page", "redirect_to_chat"
# #         }:
# #             del st.session_state[k]

# #     st.session_state["_logout_triggered"] = redirect_to
# #     st.rerun()



# # utils/session_utils.py
# def logout_user(redirect_to="app.py"):
#     """Universal logout — clear session, cookie, and trigger redirect."""
#     cookies = _get_cookies()
#     token = st.session_state.get("session_token")
#     user = st.session_state.get("user_info")

#     # --- Log audit safely ---
#     if user:
#         try:
#             log_audit(user["id"], "user_logout", {"timestamp": datetime.utcnow().isoformat()})
#         except Exception:
#             pass

#     # --- Force remove cookie from browser ---
#     cookies[COOKIE_KEY] = ""
#     cookies.save()  # ✅ sync with browser immediately

#     # --- Wipe Streamlit session keys ---
#     for key in list(st.session_state.keys()):
#         if key.startswith(("session", "user", "auth_", "messages")) or key in {
#             "user_info", "redirect_to_chat", "verified_flag",
#             "auth_mode", "auth_page"
#         }:
#             del st.session_state[key]

#     # --- Trigger redirect ---
#     st.session_state["_logout_triggered"] = redirect_to

#     # --- Immediate feedback and rerun ---
#     st.toast("✅ Logged out successfully.")
#     st.rerun()



# def handle_post_logout_redirect():
#     """Handles redirection immediately after logout."""
#     target = st.session_state.pop("_logout_triggered", None)
#     if not target:
#         return

#     st.success("✅ You’ve been logged out successfully. Redirecting...")
#     time.sleep(0.5)
#     try:
#         st.switch_page(target)
#     except Exception:
#         # Fallback for multipage mismatch
#         if target.startswith("pages/"):
#             target = target.split("pages/")[-1]
#         st.markdown(f"<meta http-equiv='refresh' content='0; url=/{target}' />",
#                     unsafe_allow_html=True)
#         st.stop()


# def load_user_session():
#     """Safely restore user session without clearing cookies or forcing stop."""
#     cookies = st.session_state.get("cookies")
#     if not cookies or not cookies.ready():
#         return False

#     token = st.session_state.get("session_token") or cookies.get("session_token", "")
#     if not token:
#         return False

#     user = get_user_by_session(token)
#     if user:
#         st.session_state["user_info"] = user
#         st.session_state["session_token"] = token
#         cookies["session_token"] = token
#         cookies.save()
#         return True

#     # ❌ Do NOT clear cookies — just leave session inactive
#     return False


















# app/utils/session_utils.py
import time
import streamlit as st
from datetime import datetime
from guardian_compliance_db import get_user_by_session, log_audit, refresh_session_expiry


COOKIE_KEY = "session_token"


# def ensure_user_session():
#     """
#     Fully database-backed session manager.
#     Keeps the user logged in even after refresh or Streamlit restart.
#     """
#     token = st.session_state.get("session_token")

#     # Try restoring from persistent cache if missing
#     if not token:
#         token = st.session_state.get("_last_valid_token")

#     if not token:
#         return None  # no session

#     user = get_user_by_session(token)
#     if user:
#         st.session_state["user_info"] = user
#         st.session_state["session_token"] = token
#         st.session_state["_last_valid_token"] = token
#         try:
#             refresh_session_expiry(token, hours=8)
#         except Exception:
#             pass
#         return user

#     # Session expired or invalid
#     return None

# def ensure_user_session():
#     """
#     Restores a valid user session without reinitializing cookies.
#     Never clears cookies automatically; handles transient reloads gracefully.
#     """
#     # --- Always initialize cookies first ---
#     cookies = st.session_state.get("cookies")
#     if not cookies:
#         from streamlit_cookies_manager import EncryptedCookieManager
#         cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")

#         if not cookies.ready():
#             st.info("🔄 Initializing secure session cookies...")
#             st.stop()

#         cookies.save()
#         st.session_state["cookies"] = cookies

#     # --- Get token (from session_state or cookies) ---
#     token = st.session_state.get("session_token") or cookies.get("session_token", "")
#     if not token:
#         return None, cookies  # no session yet

#     # --- Validate token via DB ---
#     try:
#         from guardian_compliance_db import get_user_by_session
#         user = get_user_by_session(token)
#     except Exception as e:
#         print(f"⚠️ DB lookup failed (non-fatal): {e}")
#         user = None

#     # --- Sync everything if valid ---
#     if user:
#         st.session_state["user_info"] = user
#         st.session_state["session_token"] = token
#         cookies["session_token"] = token
#         cookies.save()
#         return user, cookies

#     # --- If invalid, keep cookies intact (no forced logout) ---
#     st.session_state["user_info"] = None
#     return None, cookies



# def ensure_user_session():
#     """Safely restores a user session without crashing on missing cookies."""
#     token = st.session_state.get("session_token")
#     cookies = st.session_state.get("cookies")

#     # 🔹 Try cookie fallback if no in-memory token
#     if not token and cookies and hasattr(cookies, "get"):
#         token = cookies.get("session_token", "")

#     if not token:
#         return None, None  # no token, no session

#     # 🔹 Try to get user from DB
#     try:
#         from guardian_compliance_db import get_user_by_session
#         user = get_user_by_session(token)
#     except Exception as e:
#         print(f"⚠️ Failed to fetch user from DB: {e}")
#         user = None

#     if user:
#         st.session_state["user_info"] = user
#         st.session_state["session_token"] = token

#         # ✅ Only set cookie if manager exists
#         if cookies and hasattr(cookies, "__setitem__"):
#             try:
#                 cookies["session_token"] = token
#                 cookies.save()
#             except Exception as e:
#                 print(f"⚠️ Could not save cookie: {e}")

#         return user, token

#     return None, None

# from streamlit_cookies_manager import EncryptedCookieManager

# COOKIE_PREFIX = "guardian_"
# COOKIE_KEY = "session_token"


# def _get_cookies() -> EncryptedCookieManager:
#     """
#     Create or reuse a single EncryptedCookieManager instance.

#     - Only constructs it once per Streamlit session.
#     - Does NOT call .save() here (save only when we modify cookies).
#     """
#     if "cookies" not in st.session_state:
#         cookies = EncryptedCookieManager(
#             prefix=COOKIE_PREFIX,
#             password="super-secret-key",
#         )
#         if not cookies.ready():
#             # Let the frontend finish initializing the component
#             st.info("🔄 Restoring your secure session...")
#             st.stop()
#         st.session_state["cookies"] = cookies

#     return st.session_state["cookies"]


# def ensure_user_session():
#     """
#     Persist and restore user session reliably across refreshes.

#     ✅ Reads session_token from cookie on reload.
#     ✅ Revalidates token in DB.
#     ✅ Keeps Streamlit session_state in sync.
#     ❌ Never deletes cookies automatically.
#     """
#     cookies = _get_cookies()

#     # 1️⃣ Get token from memory or cookie
#     token = st.session_state.get("session_token") or cookies.get(COOKIE_KEY, "")
#     if not token:
#         return None  # user not logged in

#     # 2️⃣ Validate token via DB
#     try:
#         user = get_user_by_session(token)
#     except Exception as e:
#         print(f"⚠️ Session restore DB error: {e}")
#         return None

#     if not user:
#         # Token expired / invalid – do NOT clear cookie here; logout() will.
#         st.session_state["user_info"] = None
#         return None

#     # 3️⃣ Sync back into Streamlit state and cookie
#     st.session_state["user_info"] = user
#     st.session_state["session_token"] = token

#     # Only write + save cookie if needed
#     if cookies.get(COOKIE_KEY) != token:
#         cookies[COOKIE_KEY] = token
#         cookies.save()

#     return user

# def ensure_user_session():
#     """
#     Persist and restore user session reliably across refreshes.
#     ✅ Reads session_token from cookie on reload.
#     ✅ Revalidates token in DB.
#     ✅ Keeps Streamlit session_state in sync.
#     ❌ Never deletes cookies automatically.
#     """
#     # --- 1️⃣ Ensure cookie manager is initialized ---
#     if "cookies" not in st.session_state:
#         from streamlit_cookies_manager import EncryptedCookieManager
#         cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
#         if not cookies.ready():
#             st.info("🔄 Restoring your secure session...")
#             st.stop()
#         cookies.save()
#         st.session_state["cookies"] = cookies
#     else:
#         cookies = st.session_state["cookies"]

#     # --- 2️⃣ Restore token from session_state or cookie ---
#     token = st.session_state.get("session_token") or cookies.get("session_token", "")
#     if not token:
#         return None  # No active session

#     # --- 3️⃣ Validate token against DB ---
#     try:
#         from guardian_compliance_db import get_user_by_session
#         user = get_user_by_session(token)
#     except Exception as e:
#         print(f"⚠️ Session restore DB error: {e}")
#         user = None

#     # --- 4️⃣ If session valid, sync back into Streamlit ---
#     if user:
#         st.session_state["user_info"] = user
#         st.session_state["session_token"] = token
#         cookies["session_token"] = token
#         cookies.save()
#         return user

#     # --- 5️⃣ If token expired or user deleted, don't clear cookie immediately ---
#     st.session_state["user_info"] = None
#     return None

# def logout_user(redirect_to="app.py"):
#     """Logs the user out everywhere, not just Streamlit session."""
#     user = st.session_state.get("user_info")
#     token = st.session_state.get("session_token")

#     if user:
#         try:
#             log_audit(user["id"], "user_logout", {"timestamp": datetime.utcnow().isoformat()})
#         except Exception:
#             pass

#     # Clear Streamlit state
#     for key in list(st.session_state.keys()):
#         if key.startswith(("session", "user", "auth_", "messages")) or key in {
#             "user_info", "redirect_to_chat", "verified_flag", "auth_mode", "auth_page"
#         }:
#             del st.session_state[key]

#     # Trigger redirect
#     st.session_state["_logout_triggered"] = redirect_to
#     st.toast("✅ Logged out successfully.")
#     st.rerun()

# def logout_user(redirect_to="app.py"):
#     """Logs the user out everywhere, not just Streamlit session."""
#     cookies = _get_cookies()
#     user = st.session_state.get("user_info")
#     token = st.session_state.get("session_token")

#     if user:
#         try:
#             log_audit(
#                 user["id"],
#                 "user_logout",
#                 {"timestamp": datetime.utcnow().isoformat()},
#             )
#         except Exception:
#             pass

#     # 🧹 Clear cookie in browser
#     cookies[COOKIE_KEY] = ""
#     cookies.save()

#     # 🧹 Clear Streamlit state
#     for key in list(st.session_state.keys()):
#         if key.startswith(("session", "user", "auth_", "messages")) or key in {
#             "user_info", "redirect_to_chat", "verified_flag", "auth_mode", "auth_page"
#         }:
#             del st.session_state[key]

#     # Trigger redirect on next run
#     st.session_state["_logout_triggered"] = redirect_to
#     st.toast("✅ Logged out successfully.")
#     st.rerun()


# def handle_post_logout_redirect():
#     """Handles page redirect after logout."""
#     target = st.session_state.pop("_logout_triggered", None)
#     if not target:
#         return
#     st.success("✅ You’ve been logged out successfully. Redirecting...")
#     time.sleep(0.6)
#     try:
#         st.switch_page(target)
#     except Exception:
#         st.markdown(f"<meta http-equiv='refresh' content='0; url=/{target}' />", unsafe_allow_html=True)
#         st.stop()



# app/utils/session_utils.py

# import time
# from datetime import datetime
# import streamlit as st

# from guardian_compliance_db import (
#     get_user_by_session,
#     log_audit,
#     refresh_session_expiry,
# )

# # We’ll carry the token in the URL: ?session_token=<token>
# SESSION_QUERY_KEY = "session_token"


# def ensure_user_session():
#     """
#     Persist and restore user session reliably across refreshes.

#     ✅ Reads session_token from st.session_state OR URL query (?session_token=...).
#     ✅ Revalidates token in DB.
#     ✅ Keeps Streamlit session_state in sync.
#     ❌ Does NOT depend on streamlit_cookies_manager.
#     """
#     # 1️⃣ Try in-memory token first
#     token = st.session_state.get("session_token")

#     # 2️⃣ Fallback to URL query params
#     if not token:
#         qp = st.query_params
#         raw = qp.get(SESSION_QUERY_KEY)
#         if isinstance(raw, list):
#             token = raw[0] if raw else ""
#         else:
#             token = raw or ""

#     if not token:
#         # No token anywhere → not logged in
#         return None

#     # 3️⃣ Validate token in DB
#     try:
#         user = get_user_by_session(token)
#     except Exception as e:
#         print(f"⚠️ Session restore DB error: {e}")
#         return None

#     if not user:
#         # Token invalid / expired → clear in-memory state but don’t loop
#         st.session_state.pop("session_token", None)
#         st.session_state.pop("user_info", None)
#         return None

#     # 4️⃣ Sync valid session back into session_state
#     st.session_state["session_token"] = token
#     st.session_state["user_info"] = user
#     return user


# def active_session_refresh(hours: int = 8):
#     """
#     Extend session validity in DB if a token is present.
#     Call this once at the top of your pages.
#     """
#     token = st.session_state.get("session_token")
#     if not token:
#         return
#     try:
#         refresh_session_expiry(token, hours=hours)
#     except Exception as e:
#         print(f"⚠️ Failed to refresh session expiry: {e}")


# def logout_user(redirect_to: str = "pages/auth_ui.py"):
#     """
#     Logs the user out:

#     - Writes an audit event.
#     - Clears session-related keys from st.session_state.
#     - Removes session_token from URL query params.
#     - Triggers redirect on next run.
#     """
#     user = st.session_state.get("user_info")
#     token = st.session_state.get("session_token")

#     # 📝 Audit log
#     if user:
#         try:
#             log_audit(
#                 user["id"],
#                 "user_logout",
#                 {"timestamp": datetime.utcnow().isoformat(), "token": token},
#             )
#         except Exception as e:
#             print(f"⚠️ Failed to log logout event: {e}")

#     # 🧹 Clear Streamlit state
#     for key in list(st.session_state.keys()):
#         if key.startswith(("session", "user", "auth_", "messages")) or key in {
#             "user_info",
#             "redirect_to_chat",
#             "verified_flag",
#             "auth_mode",
#             "auth_page",
#         }:
#             st.session_state.pop(key, None)

#     # 🧹 Remove token from URL
#     qp = dict(st.query_params)
#     if SESSION_QUERY_KEY in qp:
#         qp.pop(SESSION_QUERY_KEY)
#         st.query_params.clear()
#         if qp:
#             st.query_params.update(qp)

#     # Trigger redirect on next run
#     st.session_state["_logout_triggered"] = redirect_to
#     st.toast("✅ Logged out successfully.")
#     st.rerun()


# def handle_post_logout_redirect():
#     """Handles page redirect after logout."""
#     target = st.session_state.pop("_logout_triggered", None)
#     if not target:
#         return

#     st.success("✅ You’ve been logged out successfully. Redirecting...")
#     time.sleep(0.6)
#     try:
#         st.switch_page(target)
#     except Exception:
#         # Fallback if switch_page path doesn’t match
#         st.markdown(
#             f"<meta http-equiv='refresh' content='0; url=/{target}' />",
#             unsafe_allow_html=True,
#         )
#         st.stop()












# app/utils/session_utils.py
import time
from datetime import datetime
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

from guardian_compliance_db import get_user_by_session, log_audit

COOKIE_PREFIX = "guardian_"
COOKIE_KEY = "session_token"


# def _get_cookies() -> EncryptedCookieManager:
#     """
#     Create a cookie manager for THIS PAGE.

#     ⚠️ Do NOT cache it in st.session_state.
#     The underlying browser cookie is shared automatically.
#     """
#     cookies = EncryptedCookieManager(
#         prefix=COOKIE_PREFIX,
#         password="super-secret-key",
#     )

#     if not cookies.ready():
#         # Wait for the component iframe to initialize
#         st.info("🔄 Restoring your secure session...")
#         st.stop()

#     return cookies

def _get_cookies():
    """Return the cookie manager created at the page level."""
    return st.session_state.get("cookies")


def ensure_user_session():
    cookies = st.session_state.get("cookies")
    if not cookies:
        return None

    token = st.session_state.get("session_token") or cookies.get("session_token", "")
    if not token:
        return None

    user = get_user_by_session(token)
    if not user:
        return None

    st.session_state["user_info"] = user
    st.session_state["session_token"] = token
    return user



# def ensure_user_session():
#     """
#     Persist and restore user session reliably across refreshes.

#     ✅ Reads session_token from cookie on reload.
#     ✅ Revalidates token in DB.
#     ✅ Keeps Streamlit session_state in sync.
#     ❌ Never deletes cookies automatically (only logout does that).
#     """
#     cookies = _get_cookies()

#     # 1️⃣ Get token from memory or cookie
#     token = st.session_state.get("session_token") or cookies.get(COOKIE_KEY, "")
#     if not token:
#         return None  # user not logged in

#     # 2️⃣ Validate token via DB
#     try:
#         user = get_user_by_session(token)
#     except Exception as e:
#         print(f"⚠️ Session restore DB error: {e}")
#         return None

#     if not user:
#         # Token expired / invalid – do NOT clear cookie here; logout() will.
#         st.session_state["user_info"] = None
#         return None

#     # 3️⃣ Sync back into Streamlit state (but DO NOT save cookie again)
#     st.session_state["user_info"] = user
#     st.session_state["session_token"] = token

#     return user


def logout_user(redirect_to="app.py"):
    """Logs the user out (DB + cookie + session_state) and redirects."""
    cookies = _get_cookies()
    user = st.session_state.get("user_info")
    token = st.session_state.get("session_token")

    if user:
        try:
            log_audit(
                user["id"],
                "user_logout",
                {"timestamp": datetime.utcnow().isoformat()},
            )
        except Exception:
            pass

    # 🧹 Clear cookie in browser
    cookies[COOKIE_KEY] = ""
    cookies.save()

    # 🧹 Clear Streamlit state
    for key in list(st.session_state.keys()):
        if key.startswith(("session", "user", "auth_", "messages")) or key in {
            "user_info", "redirect_to_chat", "verified_flag", "auth_mode", "auth_page"
        }:
            del st.session_state[key]

    # Trigger redirect on next run
    st.session_state["_logout_triggered"] = redirect_to
    st.toast("✅ Logged out successfully.")
    st.rerun()


def handle_post_logout_redirect():
    """Handles page redirect after logout."""
    target = st.session_state.pop("_logout_triggered", None)
    if not target:
        return
    st.success("✅ You’ve been logged out successfully. Redirecting...")
    time.sleep(0.6)
    try:
        st.switch_page(target)
    except Exception:
        st.markdown(
            f"<meta http-equiv='refresh' content='0; url=/{target}' />",
            unsafe_allow_html=True
        )
        st.stop()