"""Tracking Agent: persists status and surfaces the application history."""
from __future__ import annotations

from typing import List

from .base import BaseAgent
from ..models.application import Application, ApplicationStatus
from ..storage.repositories import ApplicationRepository


class TrackingAgent(BaseAgent):
    name = "ApplicationTrackingAgent"
    instructions = "Monitor and persist application status transitions for the user."

    def __init__(self, *args, repo: ApplicationRepository | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.repo = repo or ApplicationRepository()

    def update_status(self, app: Application, status: ApplicationStatus, note: str = "") -> Application:
        app.status = status
        if note:
            app.notes.append(note)
        self.repo.save(app)
        return app

    def history(self, user_id: str) -> List[Application]:
        return self.repo.list_for_user(user_id)
