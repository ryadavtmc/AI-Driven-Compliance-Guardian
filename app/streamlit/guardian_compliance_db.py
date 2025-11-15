# guardian_compliance_db.py
# ------------------------------------------------------------
# Encrypted SQLite (SQLCipher) database for local/dev
# Supports:
#   - User auth (create, verify, sessions)
#   - Email verification
#   - Forgot password / reset
#   - Policy & audit logs
# ------------------------------------------------------------

import os, json, hmac, base64, hashlib, secrets, contextlib, time
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv
import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
from typing import Optional
import streamlit as st
import time

# ------------------------------------------------------------
# Load environment early
# ------------------------------------------------------------
load_dotenv()

# DB_PATH = os.getenv("GUARDIAN_DB_PATH", os.path.abspath("./compliance_guardian.db"))
DB_PATH = os.getenv("GUARDIAN_DB_PATH", "compliance_guardian_v2.db")
DB_KEY = os.getenv("GUARDIAN_DB_KEY", "")

# ---------------------
# Email helpers
# ---------------------


def _app_base_url() -> str:
    """
    Returns the app's base URL.
    - Uses environment variable if provided (APP_BASE_URL)
    - Otherwise falls back to a local auto-detected address.
    """
    # Prefer explicit env variable for deployment
    env_url = os.getenv("APP_BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    # Try to detect local IP dynamically (e.g., 10.0.0.x)
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return f"http://{local_ip}:8501"
    except Exception:
        # Fallback for local dev
        return "http://localhost:8501"


# def db():
#     """Context manager for SQLite connection with WAL mode enabled."""
#     conn = sqlite3.connect(DB_PATH, check_same_thread=False)
#     conn.row_factory = sqlite3.Row
#     conn.execute("PRAGMA journal_mode=WAL;")
#     return conn

def upgrade_schema_v2():
    """Auto-upgrade the database schema safely if new columns are missing."""
    with db() as conn:
        cur = conn.cursor()

        # Ensure 'users' table exists
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT UNIQUE NOT NULL,
            password_hash   TEXT,
            provider        TEXT DEFAULT 'local',
            name            TEXT,
            role            TEXT DEFAULT 'user',
            is_verified     INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL,
            last_login_at   TEXT
        );
        """)

        # Check existing columns
        cur.execute("PRAGMA table_info(users)")
        existing_cols = [c[1] for c in cur.fetchall()]

        # Columns to ensure exist
        columns = {
            "provider": "TEXT DEFAULT 'local'",
            "role": "TEXT DEFAULT 'user'",
            "is_verified": "INTEGER DEFAULT 0",
            "last_login_at": "TEXT"
        }

        # Add missing columns dynamically
        for col, col_type in columns.items():
            if col not in existing_cols:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                print(f"✅ Added missing column: {col}")

        # Optional performance indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")

        conn.commit()

def send_email(recipient: str, subject: str, html_body: str):
    smtp_server = os.getenv("EMAIL_SERVER")
    smtp_port = int(os.getenv("EMAIL_PORT", 465))
    sender = os.getenv("EMAIL_FROM", os.getenv("EMAIL_USER"))
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    if not all([smtp_server, smtp_port, sender, user, password]):
        print(f"[DEV][EMAIL NOT CONFIGURED] To: {recipient} | Subject: {subject}\n{html_body}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(user, password)
        server.sendmail(sender, recipient, msg.as_string())

def _send_verification_email(email: str, token: str):
    link = f"{_app_base_url()}/auth_ui?verify={token}"
    html = f"""
    <h3>Verify your Compliance Guardian account</h3>
    <p>Click the button below to verify your email.</p>
    <p><a href="{link}" target="_blank"
          style="display:inline-block;padding:10px 16px;background:#0a66c2;color:#fff;border-radius:6px;text-decoration:none;">
          Verify my account</a></p>
    <p>If the button doesn't work, open this URL: {link}</p>
    """
    send_email(email, "Verify your Compliance Guardian account", html)

def _send_password_reset_email(email: str, token: str):
    link = f"{_app_base_url()}?reset={token}"
    html = f"""
    <h3>Reset your Compliance Guardian password</h3>
    <p>Click the button below to choose a new password.</p>
    <p><a href="{link}" target="_blank"
          style="display:inline-block;padding:10px 16px;background:#0a66c2;color:#fff;border-radius:6px;text-decoration:none;">
          Reset my password</a></p>
    <p>If the button doesn't work, open this URL: {link}</p>
    """
    send_email(email, "Reset your Compliance Guardian password", html)

# ---------------------
# SQLCipher / SQLite setup
# ---------------------
try:
    from pysqlcipher3 import dbapi2 as sqlite
    _SQLCIPHER = True
except ImportError:
    import sqlite3 as sqlite
    _SQLCIPHER = False

def _get_db_key() -> str:
    """Safely fetch GUARDIAN_DB_KEY from env — raise error if missing."""
    key = os.getenv("GUARDIAN_DB_KEY", "").strip()
    if not key and _SQLCIPHER:
        raise RuntimeError("❌ GUARDIAN_DB_KEY missing in .env (required for SQLCipher).")
    return key

_PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;",
    "PRAGMA busy_timeout=5000;",
]
_SQLCIPHER_PRAGMAS = [
    "PRAGMA cipher_compatibility = 4;",
    "PRAGMA kdf_iter = 256000;",
    "PRAGMA cipher_page_size = 4096;",
    "PRAGMA cipher_hmac_algorithm = HMAC_SHA512;",
    "PRAGMA cipher_kdf_algorithm  = PBKDF2_HMAC_SHA512;",
]

# ---------------------
# Password hashing
# ---------------------
try:
    from argon2 import PasswordHasher
    _argon2 = PasswordHasher(time_cost=2, memory_cost=64 * 1024, parallelism=1, hash_len=32)
    def hash_password(pw: str) -> str:
        return _argon2.hash(pw)
    def verify_password(pw: str, hashed: str) -> bool:
        try:
            _argon2.verify(hashed, pw)
            return True
        except Exception:
            return False
except Exception:
    def hash_password(pw: str) -> str:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000, dklen=32)
        return "pbkdf2$200000$" + base64.b64encode(salt + dk).decode()
    def verify_password(pw: str, hashed: str) -> bool:
        if not hashed.startswith("pbkdf2$"):
            return False
        _, iter_s, b64 = hashed.split("$", 2)
        blob = base64.b64decode(b64.encode())
        salt, ref = blob[:16], blob[16:]
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, int(iter_s), dklen=32)
        return hmac.compare_digest(dk, ref)

# ---------------------
# DB Connection (with retry and key fix)
# --------------------

# @contextlib.contextmanager
# def db(retries: int = 5, delay: float = 0.2):
#     conn = None
#     for attempt in range(retries):
#         try:
#             # 1️⃣ Connect to DB
#             conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
#             conn.row_factory = sqlite3.Row
#             cur = conn.cursor()

#             # 2️⃣ Set pragmas
#             cur.execute("PRAGMA foreign_keys=ON;")
#             cur.execute("PRAGMA journal_mode=WAL;")
#             cur.execute("PRAGMA synchronous=NORMAL;")

#             # 3️⃣ Verify DB validity
#             try:
#                 cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
#                 tables = {r[0] for r in cur.fetchall()}
#             except sqlite3.DatabaseError:
#                 print(f"⚠️ DB corrupted. Recreating {DB_PATH} ...")
#                 conn.close()
#                 os.remove(DB_PATH)
#                 init_db()  # Recreate DB
#                 conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
#                 conn.row_factory = sqlite3.Row
#                 cur = conn.cursor()
#                 cur.execute("PRAGMA foreign_keys=ON;")
#                 cur.execute("PRAGMA journal_mode=WAL;")
#                 cur.execute("PRAGMA synchronous=NORMAL;")
#                 tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()}

#             # 4️⃣ Auto-bootstrap schema if critical tables missing
#             critical_tables = {"users", "sessions", "chat_messages"}
#             if not critical_tables.issubset(tables):
#                 print("🛠️ Critical tables missing — bootstrapping schema...")
#                 _bootstrap_schema(conn)

#             # ✅ Yield connection
#             yield conn
#             conn.commit()
#             break

#         except sqlite3.OperationalError as e:
#             if "locked" in str(e).lower():
#                 time.sleep(delay * (2 ** attempt))
#             else:
#                 raise
#         finally:
#             if conn:
#                 try:
#                     conn.close()
#                 except Exception:
#                     pass


@contextlib.contextmanager
def db(retries: int = 5, delay: float = 0.2):
    """Yield a SQLCipher/SQLite connection with all PRAGMAs applied."""
    conn = None
    for attempt in range(retries):
        try:
            if _SQLCIPHER:
                import pysqlcipher3.dbapi2 as sqlite
                conn = sqlite.connect(DB_PATH, timeout=10, isolation_level=None)
                cur = conn.cursor()
                cur.execute(f"PRAGMA key='{DB_KEY}';")
                for p in _SQLCIPHER_PRAGMAS:
                    cur.execute(p)
            else:
                conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
                cur = conn.cursor()
            for p in _PRAGMAS:
                cur.execute(p)

            # sanity check
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            yield conn
            conn.commit()
            break

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(delay * (2 ** attempt))
            else:
                raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

# ---------------------
# Schema bootstrap
# ---------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL,
    applied_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT,
    provider        TEXT DEFAULT 'local',
    name            TEXT,
    role            TEXT DEFAULT 'user',            -- 'user' or 'admin'
    is_verified     INTEGER DEFAULT 0,              -- 0 = unverified, 1 = verified
    created_at      TEXT NOT NULL,
    last_login_at   TEXT
);

CREATE TABLE IF NOT EXISTS email_tokens (
    token           TEXT PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token           TEXT PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           TEXT UNIQUE NOT NULL,      -- ✅ renamed from old id, used in all session functions
    created_at      TEXT NOT NULL,
    last_seen       TEXT,
    expires_at      TEXT NOT NULL,
    ip              TEXT,
    user_agent      TEXT
);


CREATE TABLE IF NOT EXISTS chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_type      TEXT NOT NULL,
    event_data      TEXT,
    created_at      TEXT NOT NULL
);



CREATE TABLE IF NOT EXISTS policy_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,  -- link to user
    policy_id       TEXT NOT NULL,             -- ID or name of the policy/rule triggered
    action          TEXT NOT NULL,             -- What the system did (e.g., "redact", "alert_sent")
    findings        TEXT,                      -- JSON array of regex matches and other findings
    ip_address      TEXT,                      -- IP address of the user/device
    user_agent      TEXT,                      -- Browser / device info
    raw_content     TEXT,                      -- Original content (if allowed)
    created_at      TEXT NOT NULL              -- ISO timestamp of the event
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_policy_events_user_id ON policy_events(user_id);
CREATE INDEX IF NOT EXISTS idx_policy_events_policy_id ON policy_events(policy_id);
CREATE INDEX IF NOT EXISTS idx_policy_events_created_at ON policy_events(created_at);
CREATE INDEX IF NOT EXISTS idx_policy_events_ip ON policy_events(ip_address);
"""

# def _bootstrap_schema(conn):
#     cur = conn.cursor()
#     cur.executescript(_SCHEMA)
#     cur.execute("INSERT INTO schema_version(version, applied_at) VALUES (?, ?);",
#                 (1, datetime.now(timezone.utc).isoformat()))
#     conn.commit()


# def init_db():
#     """
#     Initialize the database if it does not exist.
#     Applies SQLCipher key if needed and bootstraps schema.
#     """
#     if not os.path.exists(DB_PATH):
#         print(f"🛠️ Creating new database: {DB_PATH}")

#         # Use the common db() context manager for SQLCipher consistency
#         with db() as conn:
#             _bootstrap_schema(conn)
#         print(f"✅ New DB created and schema applied at {DB_PATH}")

# def init_db():
#     # Check if DB exists and is valid
#     recreate = False
#     if not os.path.exists(DB_PATH):
#         recreate = True
#     else:
#         try:
#             conn = sqlite3.connect(DB_PATH)
#             conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
#             conn.close()
#         except sqlite3.DatabaseError:
#             print("⚠️ Existing DB is invalid/corrupt. Recreating...")
#             os.remove(DB_PATH)
#             recreate = True

#     if recreate:
#         conn = sqlite3.connect(DB_PATH)
#         _bootstrap_schema(conn)
#         conn.close()
#         print(f"✅ New DB created at {DB_PATH}")

 # Adjust import paths if needed

# DB_PATH = "compliance_guardian.db"



def _bootstrap_schema(conn):
    """
    Create all tables and indexes if missing.
    Only inserts into schema_version if empty.
    """
    cur = conn.cursor()
    # Execute schema script
    cur.executescript(_SCHEMA)

    # Insert initial schema_version only if not already present
    cur.execute("SELECT COUNT(*) FROM schema_version;")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO schema_version(version, applied_at) VALUES (?, ?);",
            (1, datetime.now(timezone.utc).isoformat())
        )

    conn.commit()
    print("✅ Database schema bootstrapped.")


def init_db():
    """
    Initialize the database:
    - Creates the file if missing
    - Applies SQLCipher key if needed
    - Bootstraps schema if critical tables are missing
    """
    db_exists = os.path.exists(DB_PATH)
    with db() as conn:
        cur = conn.cursor()

        # Check for critical tables
        critical_tables = {'users', 'sessions', 'chat_messages'}
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {r[0] for r in cur.fetchall()}

        if not db_exists or not critical_tables.issubset(existing_tables):
            print("🛠️ Creating or repairing database schema...")
            _bootstrap_schema(conn)
        else:
            print("✅ Database exists and critical tables are present.")




# ------------------------------------------------------------
# USER CREATION
# ------------------------------------------------------------
def create_user(email: str, password: str = "", name: str = "", role: str = "user") -> int:
    """
    Create a new user with the specified role (default 'user').
    Sends an asynchronous email verification link.
    """
    email = email.lower().strip()
    pw_hash = hash_password(password)

    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (email, password_hash, name, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email, pw_hash, name, role, datetime.now(timezone.utc).isoformat()),
        )
        user_id = cur.lastrowid
        conn.commit()

    # ✅ Send verification email asynchronously
    try:
        vtoken = create_email_verification_token(user_id)
        threading.Thread(
            target=_send_verification_email, args=(email, vtoken), daemon=True
        ).start()
    except Exception as e:
        print(f"⚠️ Warning: failed to send verification email for {email}: {e}")

    return user_id


# ------------------------------------------------------------
# AUTHENTICATION HELPERS
# ------------------------------------------------------------
def get_user_id_by_email(email: str) -> Optional[int]:
    """Fetch a user's ID by email."""
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?;", (email.lower().strip(),))
        row = cur.fetchone()
        return row[0] if row else None


def verify_user(email: str, password: str) -> Optional[int]:
    """Verify user credentials and return user_id if valid."""
    email = email.lower().strip()
    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, password_hash, is_verified FROM users WHERE email = ?;",
            (email,),
        )
        row = cur.fetchone()
        if not row:
            return None

        uid, pw_hash, verified = row
        if not verified:
            raise PermissionError("Email not verified.")

        if verify_password(password, pw_hash):
            cur.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?;",
                (datetime.now(timezone.utc).isoformat(), uid),
            )
            conn.commit()
            return uid
        return None


# ------------------------------------------------------------
# SESSION MANAGEMENT
# ------------------------------------------------------------



def create_session(user_id):
    import secrets
    token = secrets.token_hex(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
    with db() as conn:
        conn.execute("""
            INSERT INTO sessions (user_id, token, created_at, expires_at)
            VALUES (?, ?, ?, ?)
    """, (user_id, token, datetime.now(timezone.utc).isoformat(), expires_at))
        conn.commit()
    return token


def get_user_by_session(token):
    if not token:
        return None
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.name, u.email, u.role
            FROM users u
            JOIN sessions s ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > datetime('now')
        """, (token,))
        row = cur.fetchone()
        if not row:
            return None
        keys = ["id", "name", "email", "role"]
        return dict(zip(keys, row))


def refresh_session_expiry(token, hours=8):
    """Extend a session’s expiry whenever it’s used."""
    with db() as conn:
        conn.execute("""
            UPDATE sessions
            SET expires_at = datetime('now', ?)
            WHERE token = ?
        """, (f'+{hours} hours', token))
        conn.commit()



def create_email_verification_token(user_id: int, hours=24):
    token = base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO email_tokens(token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (
            token, user_id, datetime.now(timezone.utc).isoformat(),
            (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
        ))
        conn.commit()   # ✅ VERY IMPORTANT
    return token


def verify_email_token(token: str) -> bool:
    """Verify token validity and mark user as verified."""
    token = token.strip()
    if not token:
        return False

    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM email_tokens WHERE token = ? AND expires_at > ?;",
            (token, datetime.now(timezone.utc).isoformat()),
        )
        row = cur.fetchone()
        if not row:
            return False

        uid = row[0]
        cur.execute("UPDATE users SET is_verified = 1 WHERE id = ?;", (uid,))
        cur.execute("DELETE FROM email_tokens WHERE token = ?;", (token,))
        conn.commit()
        return True


# ------------------------------------------------------------
# PASSWORD RESET
# ------------------------------------------------------------
def create_password_reset_token(user_id: int, hours: int = 1) -> str:
    """Generate a short-lived token for password reset."""
    token = base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")
    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO password_reset_tokens(token, user_id, created_at, expires_at)
               VALUES (?, ?, ?, ?)""",
                (
                token,
                user_id,
                datetime.now(timezone.utc).isoformat(),
                (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(),
            ),
        )
        conn.commit()
    return token


def reset_password_with_token(token: str, new_password: str) -> bool:
    """Reset user password if the reset token is valid."""
    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM password_reset_tokens WHERE token = ? AND expires_at > ?;",
            (token, datetime.now(timezone.utc).isoformat()),
        )
        row = cur.fetchone()
        if not row:
            return False

        uid = row[0]
        cur.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?;",
            (hash_password(new_password), uid),
        )
        cur.execute("DELETE FROM password_reset_tokens WHERE token = ?;", (token,))
        conn.commit()
        return True


# ------------------------------------------------------------
# USER MANAGEMENT
# ------------------------------------------------------------
def get_all_users():
    """Fetch all registered users."""
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id ASC")
        rows = cur.fetchall()
        return [
            {"id": r[0], "name": r[1], "email": r[2], "role": r[3], "created_at": r[4]}
            for r in rows
        ]


def update_user_role(user_id: int, new_role: str):
    """Change user role (user/admin)."""
    with db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        return True


def delete_user(user_id: int):
    """Delete a user permanently."""
    with db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    
def fetch_chat_history(user_id: int, limit: int = 50) -> list[dict]:
    """Fetch recent chat messages for a user (or guest if None)."""
    with db() as conn:
        cur = conn.cursor()
        if user_id is None:
            cur.execute("""
                SELECT role, content, created_at 
                FROM chat_messages
                WHERE user_id IS NULL 
                ORDER BY id DESC 
                LIMIT ?;
            """, (limit,))
        else:
            cur.execute("""
                SELECT role, content, created_at 
                FROM chat_messages
                WHERE user_id = ? 
                ORDER BY id DESC 
                LIMIT ?;
            """, (user_id, limit))

        rows = cur.fetchall()

    # Return in chronological order
    return [
        {"role": row[0], "content": row[1], "created_at": row[2]}
        for row in reversed(rows)
    ]



def save_chat_message(user_id: int, role: str, content: str) -> int:
    """
    Save a chat message to the database.
    user_id = None for guest users.
    role = 'user' or 'assistant'
    content = message text
    """
    from datetime import datetime
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chat_messages (user_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, role, content, datetime.utcnow().isoformat()))
        conn.commit()
        return cur.lastrowid
    

def log_audit(user_id, event_type, data=None):
    """Record security & compliance-related events."""
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_logs (user_id, event_type, event_data, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            event_type,
            json.dumps(data or {}),
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()



def log_policy_event(user_id, policy_id, action, findings=None,
                     ip_address=None, user_agent=None, raw_content=None):
    """
    Log a compliance policy enforcement event.

    Parameters:
    - user_id: int | None → ID of the user triggering the event
    - policy_id: str → unique ID or name of the triggered policy
    - action: str → what the system did ("allow", "mask", "block", etc.)
    - findings: list → regex matches, PII, secrets, etc.
    - ip_address: str → optional IP of the user/device
    - user_agent: str → optional browser/device info
    - raw_content: str → original text of the message
    """
    findings = findings or []
    ip_address = ip_address or st.session_state.get("client_ip", "unknown")
    user_agent = user_agent or st.session_state.get("user_agent", "unknown")
    raw_content = raw_content or ""

    with db() as conn:
        # Ensure table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS policy_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
                policy_id       TEXT NOT NULL,
                action          TEXT NOT NULL,
                findings        TEXT,
                ip_address      TEXT,
                user_agent      TEXT,
                raw_content     TEXT,
                created_at      TEXT NOT NULL
            )
        """)

        # Insert event
        conn.execute("""
            INSERT INTO policy_events (
                user_id, policy_id, action, findings,
                ip_address, user_agent, raw_content, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            policy_id,
            action,
            json.dumps(findings),
            ip_address,
            user_agent,
            raw_content,
            datetime.utcnow().isoformat()
        ))
        conn.commit()




# ------------------------------------------------------------
# SCHEMA VALIDATION
# ------------------------------------------------------------
# try:
#     upgrade_schema_v2()
#     print("✅ Database schema verified / upgraded.")
# except Exception as e:
#     print(f"⚠️ Schema upgrade failed: {e}")



try:
    with db() as conn:
        init_db()
    print("✅ Database schema verified / upgraded.")
except Exception as e:
    print(f"⚠️ Schema upgrade failed: {e}")


