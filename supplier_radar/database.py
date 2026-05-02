import sqlite3
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self):
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_uid TEXT UNIQUE,
                    chat_id INTEGER,
                    chat_title TEXT,
                    chat_username TEXT,
                    message_id INTEGER,
                    author_id INTEGER,
                    author_username TEXT,
                    author_name TEXT,
                    text TEXT,
                    score INTEGER,
                    reasons TEXT,
                    status TEXT DEFAULT 'new',
                    created_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER UNIQUE,
                    title TEXT,
                    username TEXT,
                    members_count INTEGER,
                    source_query TEXT,
                    status TEXT,
                    joined INTEGER DEFAULT 0,
                    last_seen_at TEXT,
                    created_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            conn.commit()

    def add_lead(self, data: dict[str, Any]) -> bool:
        with self.connect() as conn:
            try:
                conn.execute("""
                    INSERT INTO leads (
                        message_uid, chat_id, chat_title, chat_username, message_id,
                        author_id, author_username, author_name, text, score, reasons,
                        status, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
                """, (
                    data["message_uid"],
                    data.get("chat_id"),
                    data.get("chat_title"),
                    data.get("chat_username"),
                    data.get("message_id"),
                    data.get("author_id"),
                    data.get("author_username"),
                    data.get("author_name"),
                    data.get("text"),
                    data.get("score"),
                    data.get("reasons"),
                    now_iso(),
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_recent_leads(self, limit: int = 10):
        with self.connect() as conn:
            return conn.execute("""
                SELECT * FROM leads
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()

    def update_lead_status(self, lead_id: int, status: str):
        with self.connect() as conn:
            conn.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
            conn.commit()

    def stats(self):
        with self.connect() as conn:
            total_leads = conn.execute("SELECT COUNT(*) AS c FROM leads").fetchone()["c"]
            new_leads = conn.execute("SELECT COUNT(*) AS c FROM leads WHERE status = 'new'").fetchone()["c"]
            valid_leads = conn.execute("SELECT COUNT(*) AS c FROM leads WHERE status = 'valid'").fetchone()["c"]
            spam_leads = conn.execute("SELECT COUNT(*) AS c FROM leads WHERE status = 'spam'").fetchone()["c"]
            groups = conn.execute("SELECT COUNT(*) AS c FROM groups").fetchone()["c"]
            joined = conn.execute("SELECT COUNT(*) AS c FROM groups WHERE joined = 1").fetchone()["c"]
            return {
                "total_leads": total_leads,
                "new_leads": new_leads,
                "valid_leads": valid_leads,
                "spam_leads": spam_leads,
                "groups": groups,
                "joined": joined,
            }

    def upsert_group(self, data: dict[str, Any]):
        with self.connect() as conn:
            conn.execute("""
                INSERT INTO groups (
                    chat_id, title, username, members_count, source_query,
                    status, joined, last_seen_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title = excluded.title,
                    username = excluded.username,
                    members_count = excluded.members_count,
                    source_query = COALESCE(excluded.source_query, groups.source_query),
                    status = excluded.status,
                    joined = MAX(groups.joined, excluded.joined),
                    last_seen_at = excluded.last_seen_at
            """, (
                data.get("chat_id"),
                data.get("title"),
                data.get("username"),
                data.get("members_count"),
                data.get("source_query"),
                data.get("status"),
                1 if data.get("joined") else 0,
                now_iso(),
                now_iso(),
            ))
            conn.commit()

    def list_groups(self, limit: int = 20):
        with self.connect() as conn:
            return conn.execute("""
                SELECT * FROM groups
                ORDER BY last_seen_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

    def count_auto_joins_today(self) -> int:
        # Упрощенно: считаем общее число joined.
        # Для MVP достаточно. Можно расширить отдельной таблицей join_history.
        with self.connect() as conn:
            return conn.execute("SELECT COUNT(*) AS c FROM groups WHERE joined = 1").fetchone()["c"]

    def set_state(self, key: str, value: str | None):
        with self.connect() as conn:
            if value is None:
                conn.execute("DELETE FROM state WHERE key = ?", (key,))
            else:
                conn.execute("""
                    INSERT INTO state(key, value) VALUES(?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """, (key, value))
            conn.commit()

    def get_state(self, key: str, default: str | None = None):
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def discovery_status(self):
        keys = [
            "discovery_running",
            "discovery_last_start",
            "discovery_last_finish",
            "discovery_last_summary",
            "discovery_next_run",
            "discovery_floodwait_until",
            "discovery_last_error",
        ]
        return {key: self.get_state(key) for key in keys}
