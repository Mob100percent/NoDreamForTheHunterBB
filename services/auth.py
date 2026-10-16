import uuid
from datetime import datetime, timedelta
from database import get_db
from config import SESSION_EXPIRY_HOURS

def get_or_create_user(platform_account_id: str, language_id: int, region_id: int, issuer_id: int) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE platform_account_id = ?", (platform_account_id,))
    row = c.fetchone()
    if row:
        user_id = row["id"]
    else:
        c.execute(
            "INSERT INTO users (platform_account_id, language_id, region_id, issuer_id) VALUES (?, ?, ?, ?)",
            (platform_account_id, language_id, region_id, issuer_id)
        )
        conn.commit()
        user_id = c.lastrowid
    conn.close()
    return user_id

def create_session(user_id: int) -> str:
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)",
        (session_id, user_id, expires_at.isoformat())
    )
    conn.commit()
    conn.close()
    return session_id

def validate_session(session_id: str, user_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT user_id, expires_at FROM sessions WHERE session_id = ?",
        (session_id,)
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    if row["user_id"] != user_id:
        return False
    if row["expires_at"]:
        expires = datetime.fromisoformat(row["expires_at"])
        if datetime.utcnow() > expires:
            return False
    return True

def ensure_user_exists(user_id: int):
    """
    Ensure a user record exists for the given ID.
    If not, insert a minimal entry (used to prevent foreign key errors).
    """
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (id, platform_account_id, language_id, region_id, issuer_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, f"user_{user_id}", 0, 0, 0)
        )
        conn.commit()
    conn.close()