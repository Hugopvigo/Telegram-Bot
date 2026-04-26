import sqlite3
import threading
from app.config import DB_PATH

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            provincia_code TEXT NOT NULL,
            provincia_name TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            alert_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, alert_id)
        )
    """)
    conn.commit()


def add_user(chat_id: int, provincia_code: str, provincia_name: str):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO users (chat_id, provincia_code, provincia_name) VALUES (?, ?, ?)",
        (chat_id, provincia_code, provincia_name),
    )
    conn.commit()


def remove_user(chat_id: int):
    conn = _get_conn()
    conn.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
    conn.execute("DELETE FROM sent_alerts WHERE chat_id = ?", (chat_id,))
    conn.commit()


def get_all_users() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT chat_id, provincia_code, provincia_name FROM users").fetchall()
    return [dict(r) for r in rows]


def get_user(chat_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT chat_id, provincia_code, provincia_name FROM users WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    return dict(row) if row else None


def mark_alert_sent(chat_id: int, alert_id: str):
    conn = _get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO sent_alerts (chat_id, alert_id) VALUES (?, ?)",
        (chat_id, alert_id),
    )
    conn.commit()


def is_alert_sent(chat_id: int, alert_id: str) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM sent_alerts WHERE chat_id = ? AND alert_id = ?",
        (chat_id, alert_id),
    ).fetchone()
    return row is not None


def cleanup_old_alerts(days: int = 7):
    conn = _get_conn()
    conn.execute(
        "DELETE FROM sent_alerts WHERE sent_at < datetime('now', ?)",
        (f"-{days} days",),
    )
    conn.commit()
