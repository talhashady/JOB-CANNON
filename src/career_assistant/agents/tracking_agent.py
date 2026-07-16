"""Tracking Agent: persists status and surfaces the application history."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from .base import BaseAgent
from ..models.application import Application, ApplicationStatus
from ..storage.repositories import ApplicationRepository

_VALID_TRANSITIONS = {
    ApplicationStatus.DRAFT: {
        ApplicationStatus.QUEUED,
        ApplicationStatus.DRY_RUN,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.REJECTED_BY_GUARDRAIL,
        ApplicationStatus.RATE_LIMITED,
        ApplicationStatus.ERROR,
    },
    ApplicationStatus.QUEUED: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.DRY_RUN,
        ApplicationStatus.RATE_LIMITED,
        ApplicationStatus.ERROR,
    },
    ApplicationStatus.DRY_RUN: {
        ApplicationStatus.SUBMITTED,  # Allowing promotion to live
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.CLOSED,
        ApplicationStatus.ERROR,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.OFFER,
        ApplicationStatus.CLOSED,
        ApplicationStatus.ERROR,
    },
    ApplicationStatus.OFFER: {
        ApplicationStatus.CLOSED,
    },
    # Terminal states - no transitions allowed out of them except retry
    ApplicationStatus.CLOSED: set(),
    ApplicationStatus.REJECTED_BY_GUARDRAIL: {
        ApplicationStatus.QUEUED,
        ApplicationStatus.SUBMITTED,
    },
    ApplicationStatus.RATE_LIMITED: {
        ApplicationStatus.QUEUED,
        ApplicationStatus.SUBMITTED,
    },
    ApplicationStatus.ERROR: {
        ApplicationStatus.QUEUED,
        ApplicationStatus.SUBMITTED,
    },
}


class TrackingAgent(BaseAgent):
    name = "ApplicationTrackingAgent"
    instructions = "Monitor and persist application status transitions for the user."

    def __init__(self, *args, repo: ApplicationRepository | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.repo = repo or ApplicationRepository()

    def update_status(self, app: Application, status: ApplicationStatus, note: str = "") -> Application:
        current = app.status
        if current == status:
            return app

        allowed = _VALID_TRANSITIONS.get(current)
        # If the transition is explicitly restricted and target status is not allowed, reject it
        if allowed is not None and status not in allowed:
            self.log.warning(
                "Illegal status transition rejected for application %s: %s -> %s",
                app.id, current.value, status.value
            )
            return app

        app.status = status
        app.updated_at = datetime.now(timezone.utc)
        if note:
            app.notes.append(note)
        self.repo.save(app)
        return app

    def history(self, user_id: str) -> List[Application]:
        return self.repo.list_for_user(user_id)
