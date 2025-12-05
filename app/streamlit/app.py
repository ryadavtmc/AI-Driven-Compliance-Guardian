import streamlit as st
from utils.ui_utils import hide_auth_ui_link
from utils.navbar import inject_global_styles, render_navbar, add_navbar_spacer, render_footer

st.set_page_config(
    page_title="🏠 Home | AI-Driven Compliance Guardian",
    page_icon="🛡️",
    layout="wide"
)
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# MUST EXIST EXACTLY ONCE IN THE APP (Cookie Manager)
# ============================================================
cookies = EncryptedCookieManager(prefix="guardian_", password="super-secret-key")
if not cookies.ready():
    st.stop()

st.session_state["cookies"] = cookies


# ============================================================
# 🔐 ADD SESSION RESTORE HERE (RIGHT AFTER COOKIE INIT)
# ============================================================
from utils.session_utils import ensure_user_session, active_session_refresh, handle_post_logout_redirect

handle_post_logout_redirect()
active_session_refresh()
user = ensure_user_session()
active_session_refresh()

hide_auth_ui_link()

def landing_page():

  # # =============== GLOBAL STYLING ===============
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


  /* ===== FEATURES ===== */
  .features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px,1fr));
    gap: 2rem;
    padding: 8vh 3rem;
    margin-top: 6vh;
  }
  .feature {
    background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 2rem 1.5rem;
    text-align: center;
    box-shadow: 0 4px 18px rgba(0,0,0,0.3);
    transition: all 0.25s ease;
  }
  .feature:hover {
    transform: translateY(-6px);
    box-shadow: 0 10px 32px rgba(118,75,162,0.35);
  }
  .feature h3 { font-size: 1.2rem; margin-bottom: 0.6rem; font-weight: 700; }
  .feature p { font-size: 0.95rem; color: rgba(255,255,255,0.7); line-height: 1.5; }

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
  </style>
  """, unsafe_allow_html=True)



  # # =============== HERO SECTION (clean + responsive, no heavy CSS) ===============

  # Small spacer so content sits nicely below your navbar
  st.markdown("<div style='height:15vh'></div>", unsafe_allow_html=True)

  # 3-column frame to keep everything centered on any screen
  frame_left, frame_center, frame_right = st.columns([1, 2, 1])

  with frame_center:
      # Title
      st.markdown(
          """
          <h1 style="
              text-align:center;
              font-weight:800;
              line-height:1.1;
              margin: 0 0 12px 0;
              font-size: clamp(2.4rem, 5vw, 4rem);
              background: linear-gradient(135deg, #ffffff, #cfcfcf);
              -webkit-background-clip: text;
              -webkit-text-fill-color: transparent;">
              Compliance without compromise.
          </h1>
          """,
          unsafe_allow_html=True,
      )

      # Subtitle
      st.markdown(
          """
          <p style="
              text-align:center;
              color: rgba(255,255,255,0.78);
              font-size: clamp(1rem, 2.2vw, 1.15rem);
              line-height: 1.6;
              margin: 0 auto 28px auto;
              max-width: 720px;">
              Detect and mask sensitive data in real time.<br>
              Ensure privacy, compliance, and trust in every message.
          </p>
          """,
          unsafe_allow_html=True,
      )

      # Center the button using one inner row of columns
      btn_l, btn_c, btn_r = st.columns([1, 2, 1])
      with btn_c:
          clicked = st.button(
              "💬 Try Demo Chat",
              key="try_demo",
              use_container_width=True
          )
          if clicked:
              st.switch_page("pages/chat.py")

  # Subtle spacer below hero
  st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)

  # Optional: light polish for the button (kept VERY minimal)
  st.markdown(
      """
      <style>
      .stButton > button {
          border-radius: 12px !important;
          padding: 0.9rem 1.4rem !important;
          font-weight: 700 !important;
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
      </style>
      """,
      unsafe_allow_html=True,
  )


  # # =============== FEATURES ===============
  st.markdown("""
  <div class="features">
    <div class="feature">
      <h3>🔍 Real-time Detection</h3>
      <p>Identify and mask PII, PHI, and confidential data before it leaves your system.</p>
    </div>
    <div class="feature">
      <h3>🧠 AI-Powered Insights</h3>
      <p>Leverage advanced LLMs to analyze compliance context and prevent data leaks.</p>
    </div>
    <div class="feature">
      <h3>🔒 Secure by Design</h3>
      <p>End-to-end encryption, zero data retention, and enterprise-grade access control.</p>
    </div>
    <div class="feature">
      <h3>📈 Transparent Audits</h3>
      <p>Generate detailed compliance logs for accountability and governance.</p>
    </div>
  </div>
  """, unsafe_allow_html=True)

if __name__ == "__main__":
  inject_global_styles()
  # Render the navbar
  render_navbar(namespace="home")
  # Add spacing below navbar so content doesn’t overlap
  add_navbar_spacer()
  landing_page()

  render_footer()






