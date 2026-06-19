"""Repositories: the only place that touches SQL. Agents/tools talk to these."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..models.application import Application, ApplicationStatus
from ..models.job import Job
from ..models.profile import UserProfile
from .database import Database, get_database


class JobRepository:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def upsert(self, job: Job) -> None:
        self.db.execute(
            "INSERT INTO jobs (id, payload, verified) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, verified=excluded.verified",
            (job.id, job.model_dump_json(), int(job.verified)),
        )

    def upsert_many(self, jobs: List[Job]) -> int:
        for job in jobs:
            self.upsert(job)
        return len(jobs)

    def get(self, job_id: str) -> Optional[Job]:
        rows = self.db.query("SELECT payload FROM jobs WHERE id = ?", (job_id,))
        return Job.model_validate_json(rows[0]["payload"]) if rows else None

    def list_verified(self) -> List[Job]:
        rows = self.db.query("SELECT payload FROM jobs WHERE verified = 1")
        return [Job.model_validate_json(r["payload"]) for r in rows]


class ProfileRepository:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def save(self, profile: UserProfile) -> None:
        self.db.execute(
            "INSERT INTO profiles (user_id, payload, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (profile.user_id, profile.model_dump_json(), datetime.utcnow().isoformat()),
        )

    def get(self, user_id: str) -> Optional[UserProfile]:
        rows = self.db.query("SELECT payload FROM profiles WHERE user_id = ?", (user_id,))
        return UserProfile.model_validate_json(rows[0]["payload"]) if rows else None


class ApplicationRepository:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def save(self, app: Application) -> None:
        app.updated_at = datetime.utcnow()
        self.db.execute(
            "INSERT INTO applications (id, user_id, job_id, status, platform, payload, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status, payload=excluded.payload, "
            "updated_at=excluded.updated_at",
            (
                app.id,
                app.user_id,
                app.job_id,
                app.status.value,
                app.platform,
                app.model_dump_json(),
                app.updated_at.isoformat(),
            ),
        )

    def get(self, app_id: str) -> Optional[Application]:
        rows = self.db.query("SELECT payload FROM applications WHERE id = ?", (app_id,))
        return Application.model_validate_json(rows[0]["payload"]) if rows else None

    def list_for_user(self, user_id: str) -> List[Application]:
        rows = self.db.query(
            "SELECT payload FROM applications WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [Application.model_validate_json(r["payload"]) for r in rows]

    def count_submitted_today(self, platform: str) -> int:
        """Used by the rate-limit guardrail. Counts submitted/dry_run today (UTC)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = self.db.query(
            "SELECT COUNT(*) AS c FROM applications "
            "WHERE platform = ? AND status IN (?, ?) AND substr(created_at, 1, 10) = ?",
            (platform, ApplicationStatus.SUBMITTED.value, ApplicationStatus.DRY_RUN.value, today),
        )
        return int(rows[0]["c"]) if rows else 0
