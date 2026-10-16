import sqlite3
from config import DB_PATH


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # WAL: readers never block writers, writers never block readers, and
    # the webapp can read the live DB alongside the game server safely.
    # journal_mode is persistent (set once per database file); busy_timeout
    # makes writers wait for the WAL write lock instead of failing.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn