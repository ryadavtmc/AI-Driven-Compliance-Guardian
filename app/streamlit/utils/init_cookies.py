import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

def init_cookies():
    if "cookies" not in st.session_state:
        cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
        if not cookies.ready():
            st.stop()
        st.session_state["cookies"] = cookies

    return st.session_state["cookies"]

