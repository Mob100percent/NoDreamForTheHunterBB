# services/character.py
from database import get_db

DEFAULT_SHELL_INFO = "AQAAAAAAAAA="
DEFAULT_SHELL_INFO_VERSION = 2


def get_messenger_shell(chara_id: str, user_id: int):
    """The author's uploaded messenger shell (from /messenger_shell/upload),
    or the game's default shell when the player never uploaded one."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT shell_data, shell_data_version FROM messenger_shells "
        "WHERE chara_id = ? AND user_id = ?",
        (str(chara_id), user_id),
    )
    row = c.fetchone()
    conn.close()
    if row and row["shell_data"]:
        return row["shell_data"], int(row["shell_data_version"] or 0)
    return DEFAULT_SHELL_INFO, DEFAULT_SHELL_INFO_VERSION


def ensure_character(chara_id: str, user_id: int):
    """
    Ensures a character record exists for the given chara_id and user_id.
    If the combination already exists, do nothing.
    Otherwise, insert a new record.
    This allows different users to share the same chara_id.
    """
    conn = get_db()
    c = conn.cursor()

    # Check if the combination already exists
    c.execute(
        "SELECT id FROM characters WHERE chara_id = ? AND user_id = ?",
        (chara_id, user_id)
    )
    existing = c.fetchone()

    if not existing:
        c.execute(
            "INSERT INTO characters (chara_id, user_id) VALUES (?, ?)",
            (chara_id, user_id)
        )
        conn.commit()

    conn.close()