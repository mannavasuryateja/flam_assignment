# core/config.py
import sqlite3
from pathlib import Path

DEFAULTS = {
    "max_retries": "3",
    "backoff_base": "2",
    "poll_interval_ms": "500",
    "default_timeout_secs": "60",
}

class ConfigStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()
        for k, v in DEFAULTS.items():
            if self.get(k) is None:
                self.set(k, v)

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

    def set(self, key: str, value: str):
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO config(key,value) VALUES(?,?)", (key, str(value)))

    def get(self, key: str):
        with self._conn() as c:
            row = c.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
            return row["value"] if row else None

    def all(self):
        with self._conn() as c:
            return {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM config")}
