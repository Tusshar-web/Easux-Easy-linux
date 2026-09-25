"""
Storage repository providing high-level database operations.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from ai_terminal.storage.database import Database


def sha256_hash(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_SETTINGS = {
    "provider": "auto",
    "model": "gpt-4o-mini",
    "api_key_env": "AI_TERMINAL_API_KEY",
    "retention_days": "90",
    "error_retention_days": "7",
    "privacy_mode": "least_context",
    "context_enabled": "true",
    "max_suggestions": "5",
    "weight_prefix": "45",
    "weight_context": "25",
    "weight_recency": "15",
    "weight_frequency": "10",
    "weight_source": "5",
}


class Repository:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self._ensure_default_settings()

    def _ensure_default_settings(self) -> None:
        with self.db.get_connection() as conn:
            for k, v in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                    (k, v, utc_now_iso())
                )

    # --- Settings ---
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.db.get_connection() as conn:
            cur = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            if row:
                return row["value"]
            return default if default is not None else DEFAULT_SETTINGS.get(key)

    def set_setting(self, key: str, value: str) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, str(value), utc_now_iso())
            )

    def get_all_settings(self) -> Dict[str, str]:
        with self.db.get_connection() as conn:
            cur = conn.execute("SELECT key, value FROM settings ORDER BY key ASC")
            return {row["key"]: row["value"] for row in cur.fetchall()}

    # --- Command Events ---
    def record_command(self, command: str, cwd: str, exit_code: int = 0) -> None:
        cmd_strip = command.strip()
        if not cmd_strip:
            return
        cmd_h = sha256_hash(cmd_strip)
        cwd_h = sha256_hash(str(cwd))
        # Keep a short preview for display, up to 200 chars
        preview = cmd_strip[:200]

        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO command_events (command_hash, command_preview, cwd_hash, exit_code, occurred_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (cmd_h, preview, cwd_h, exit_code, utc_now_iso())
            )

    def get_recent_and_frequent_commands(self, cwd: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            if cwd:
                cwd_h = sha256_hash(str(cwd))
                cur = conn.execute(
                    """
                    SELECT command_preview, command_hash, MAX(occurred_at) as last_seen, COUNT(*) as freq
                    FROM command_events
                    WHERE cwd_hash = ?
                    GROUP BY command_hash
                    ORDER BY last_seen DESC, freq DESC
                    LIMIT ?
                    """,
                    (cwd_h, limit)
                )
            else:
                cur = conn.execute(
                    """
                    SELECT command_preview, command_hash, MAX(occurred_at) as last_seen, COUNT(*) as freq
                    FROM command_events
                    GROUP BY command_hash
                    ORDER BY last_seen DESC, freq DESC
                    LIMIT ?
                    """,
                    (limit,)
                )

            return [
                {
                    "command": row["command_preview"],
                    "hash": row["command_hash"],
                    "last_seen": row["last_seen"],
                    "frequency": row["freq"]
                }
                for row in cur.fetchall()
            ]

    # --- Suggestion Events ---
    def record_suggestion_event(self, context_hash: str, candidate: str, source: str, accepted: bool = False) -> int:
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO suggestion_events (context_hash, candidate, source, accepted, occurred_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (context_hash, candidate, source, 1 if accepted else 0, utc_now_iso())
            )
            return cur.lastrowid or 0

    def mark_suggestion_accepted(self, candidate: str, source: str = "context") -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO suggestion_events (context_hash, candidate, source, accepted, occurred_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("manual_selection", candidate, source, 1, utc_now_iso())
            )

    def get_suggestion_stats(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) as total, SUM(accepted) as accepted FROM suggestion_events")
            row = cur.fetchone()
            total = row["total"] or 0
            accepted = row["accepted"] or 0
            ratio = (accepted / total) if total > 0 else 0.0
            return {
                "total_suggestions": total,
                "accepted_suggestions": accepted,
                "acceptance_rate": round(ratio * 100, 1),
            }

    # --- Project Cache ---
    def get_cached_project(self, root_path: str, max_age_seconds: int = 300) -> Optional[Dict[str, Any]]:
        root_h = sha256_hash(root_path)
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "SELECT kind, metadata_json, scanned_at FROM project_cache WHERE root_hash = ?",
                (root_h,)
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                scanned_dt = datetime.fromisoformat(row["scanned_at"])
                age = (datetime.now(timezone.utc) - scanned_dt).total_seconds()
                if age > max_age_seconds:
                    return None
                data = json.loads(row["metadata_json"])
                data["_kind"] = row["kind"]
                return data
            except Exception:
                return None

    def set_cached_project(self, root_path: str, kind: str, metadata: Dict[str, Any]) -> None:
        root_h = sha256_hash(root_path)
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO project_cache (root_hash, kind, metadata_json, scanned_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(root_hash) DO UPDATE SET kind = excluded.kind, metadata_json = excluded.metadata_json, scanned_at = excluded.scanned_at",
                (root_h, kind, json.dumps(metadata), utc_now_iso())
            )

    # --- Error Events ---
    def record_error_event(self, command: str, exit_code: int, stderr_redacted: str) -> None:
        cmd_h = sha256_hash(command.strip())
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO error_events (command_hash, stderr_redacted, exit_code, occurred_at) VALUES (?, ?, ?, ?)",
                (cmd_h, stderr_redacted, exit_code, utc_now_iso())
            )

    def get_latest_error(self) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "SELECT command_hash, stderr_redacted, exit_code, occurred_at FROM error_events ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                return {
                    "command_hash": row["command_hash"],
                    "stderr": row["stderr_redacted"],
                    "exit_code": row["exit_code"],
                    "occurred_at": row["occurred_at"]
                }
            return None

    # --- Risk Overrides ---
    def add_risk_override(self, rule_id: str, scope: str, duration_minutes: int = 60) -> None:
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).isoformat()
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO risk_overrides (rule_id, scope, expires_at) VALUES (?, ?, ?)",
                (rule_id, scope, expires_at)
            )

    def is_risk_overridden(self, rule_id: str, scope: str) -> bool:
        now_str = utc_now_iso()
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "SELECT id FROM risk_overrides WHERE rule_id = ? AND (scope = ? OR scope = '*') AND expires_at > ?",
                (rule_id, scope, now_str)
            )
            return cur.fetchone() is not None

    # --- Retention & Purge ---
    def purge_retention(self) -> Dict[str, int]:
        retention_days = int(self.get_setting("retention_days", "90") or 90)
        error_days = int(self.get_setting("error_retention_days", "7") or 7)

        now = datetime.now(timezone.utc)
        cmd_cutoff = (now - timedelta(days=retention_days)).isoformat()
        err_cutoff = (now - timedelta(days=error_days)).isoformat()

        with self.db.get_connection() as conn:
            c1 = conn.execute("DELETE FROM command_events WHERE occurred_at < ?", (cmd_cutoff,)).rowcount
            c2 = conn.execute("DELETE FROM suggestion_events WHERE occurred_at < ?", (cmd_cutoff,)).rowcount
            c3 = conn.execute("DELETE FROM error_events WHERE occurred_at < ?", (err_cutoff,)).rowcount
            c4 = conn.execute("DELETE FROM risk_overrides WHERE expires_at < ?", (now.isoformat(),)).rowcount

        return {
            "purged_command_events": c1,
            "purged_suggestion_events": c2,
            "purged_error_events": c3,
            "purged_overrides": c4,
        }

    def clear_all_data(self) -> Dict[str, int]:
        with self.db.get_connection() as conn:
            c1 = conn.execute("DELETE FROM command_events").rowcount
            c2 = conn.execute("DELETE FROM suggestion_events").rowcount
            c3 = conn.execute("DELETE FROM error_events").rowcount
            c4 = conn.execute("DELETE FROM project_cache").rowcount
            c5 = conn.execute("DELETE FROM risk_overrides").rowcount

        return {
            "deleted_command_events": c1,
            "deleted_suggestion_events": c2,
            "deleted_error_events": c3,
            "deleted_project_cache": c4,
            "deleted_risk_overrides": c5,
        }

    # --- Export ---
    def export_data(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            settings_rows = [dict(r) for r in conn.execute("SELECT * FROM settings").fetchall()]
            cmd_rows = [dict(r) for r in conn.execute("SELECT * FROM command_events LIMIT 1000").fetchall()]
            sugg_rows = [dict(r) for r in conn.execute("SELECT * FROM suggestion_events LIMIT 1000").fetchall()]
            err_rows = [dict(r) for r in conn.execute("SELECT * FROM error_events LIMIT 500").fetchall()]
            overrides = [dict(r) for r in conn.execute("SELECT * FROM risk_overrides").fetchall()]

        return {
            "exported_at": utc_now_iso(),
            "settings": settings_rows,
            "command_events": cmd_rows,
            "suggestion_events": sugg_rows,
            "error_events": err_rows,
            "risk_overrides": overrides,
        }
