"""Application Agent: rate-limited, dry-run-by-default submission."""
from __future__ import annotations

import uuid

from .base import BaseAgent
from ..guardrails.rate_limiter import RateLimiter
from ..models.application import Application, ApplicationStatus
from ..models.job import Job
from ..storage.repositories import ApplicationRepository
from ..tools import application_submit


class ApplicationAgent(BaseAgent):
    name = "ApplicationAutomationAgent"
    instructions = (
        "Submit applications respecting a per-platform daily cap. Default to dry-run; only "
        "submit live when explicitly enabled and a backend is registered."
    )

    def __init__(self, *args, repo: ApplicationRepository | None = None,
                 rate_limiter: RateLimiter | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.repo = repo or ApplicationRepository()
        self.rate_limiter = rate_limiter or RateLimiter(self.repo)

    def run(self, user_id: str, job: Job, resume_text: str, cover_letter_text: str) -> Application:
        app = Application(
            id=str(uuid.uuid4()),
            user_id=user_id,
            job_id=job.id,
            platform=job.source,
            status=ApplicationStatus.QUEUED,
        )

        gate = self.rate_limiter.check(job.source)
        if not gate.passed:
            app.status = ApplicationStatus.RATE_LIMITED
            app.notes.extend(gate.issues)
            self.repo.save(app)
            self.log.warning("Application rate-limited for %s.", job.source)
            return app

        status, detail = application_submit.submit_application(job, resume_text, cover_letter_text)
        if status == "submitted":
            app.status = ApplicationStatus.SUBMITTED
        elif status == "dry_run":
            app.status = ApplicationStatus.DRY_RUN
        else:
            app.status = ApplicationStatus.ERROR
        app.notes.append(f"submit:{status}:{detail.get('mode', '')}")
        self.repo.save(app)
        return app
