"""
SQLite database setup and schema management.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional


DEFAULT_DB_DIR = Path.home() / ".local" / "share" / "ai_terminal"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "ai_terminal.db"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS command_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_hash TEXT NOT NULL,
    command_preview TEXT NOT NULL,
    cwd_hash TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cmd_events_cwd ON command_events(cwd_hash, occurred_at);
CREATE INDEX IF NOT EXISTS idx_cmd_events_hash ON command_events(command_hash);

CREATE TABLE IF NOT EXISTS suggestion_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_hash TEXT NOT NULL,
    candidate TEXT NOT NULL,
    source TEXT NOT NULL,
    accepted INTEGER NOT NULL DEFAULT 0,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sugg_events_ctx ON suggestion_events(context_hash);
CREATE INDEX IF NOT EXISTS idx_sugg_events_cand ON suggestion_events(candidate);

CREATE TABLE IF NOT EXISTS project_cache (
    root_hash TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    scanned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS error_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_hash TEXT NOT NULL,
    stderr_redacted TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_error_events_occurred ON error_events(occurred_at);

CREATE TABLE IF NOT EXISTS risk_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                base_dir = Path(xdg_data) / "ai_terminal"
            else:
                base_dir = DEFAULT_DB_DIR
            self.db_path = base_dir / "ai_terminal.db"

        self._ensure_db_dir()
        self._init_schema()

    def _ensure_db_dir(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=5.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.OperationalError:
            pass
        return conn

    def _init_schema(self) -> None:
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
