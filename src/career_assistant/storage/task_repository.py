"""Task repository for persisting background pipeline jobs and results."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from .database import Database, get_database

# Defaults (overridable via Settings if needed in future)
TASK_TTL_HOURS = 72
MAX_RESULT_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_CONCURRENT_TASKS_PER_USER = 3


class TaskRepository:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def create(self, task_id: str, user_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO tasks (id, user_id, status, result, error, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, user_id, "pending", None, None, now, now),
        )

    def update(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        res_json: Optional[str] = None
        result_truncated = False
        if result is not None:
            res_json = json.dumps(result)
            if len(res_json) > MAX_RESULT_BYTES:
                # Store a truncated marker instead of the oversized payload
                res_json = json.dumps({
                    "result_truncated": True,
                    "jobs_scraped": result.get("jobs_scraped"),
                    "jobs_verified": result.get("jobs_verified"),
                    "is_demo": result.get("is_demo"),
                    "data_source": result.get("data_source"),
                    "elapsed_s": result.get("elapsed_s"),
                    "recommendation_count": len(result.get("recommendations", [])),
                    "note": f"Full result exceeded {MAX_RESULT_BYTES // (1024*1024)} MB limit and was truncated.",
                })
                result_truncated = True
        self.db.execute(
            "UPDATE tasks SET status = ?, result = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, res_json, error, now, task_id),
        )

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        rows = self.db.query("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not rows:
            return None
        r = rows[0]
        result_val = json.loads(r["result"]) if r["result"] else None
        return {
            "id": r["id"],
            "user_id": r["user_id"],
            "status": r["status"],
            "result": result_val,
            "error": r["error"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }

    def count_active_for_user(self, user_id: str) -> int:
        """Count pending or running tasks for a user."""
        rows = self.db.query(
            "SELECT COUNT(*) AS c FROM tasks WHERE user_id = ? AND status IN (?, ?)",
            (user_id, "pending", "running"),
        )
        return int(rows[0]["c"]) if rows else 0

    def cleanup_expired(self) -> int:
        """Delete tasks older than TASK_TTL_HOURS. Returns number of rows deleted."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=TASK_TTL_HOURS)).isoformat()
        # Only clean up completed (done/error) tasks past TTL
        self.db.execute(
            "DELETE FROM tasks WHERE status IN (?, ?) AND updated_at < ?",
            ("done", "error", cutoff),
        )
        # We can't easily get rowcount from the generic DB interface, so just return 0
        return 0

    def expire_stale_running(self, max_age_seconds: int = 600) -> None:
        """Mark tasks stuck in 'pending' or 'running' for longer than max_age_seconds as 'error'."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)).isoformat()
        self.db.execute(
            "UPDATE tasks SET status = ?, error = ?, updated_at = ? "
            "WHERE status IN (?, ?) AND updated_at < ?",
            (
                "error",
                "Task execution timed out or server restarted while processing.",
                datetime.now(timezone.utc).isoformat(),
                "pending",
                "running",
                cutoff,
            ),
        )

