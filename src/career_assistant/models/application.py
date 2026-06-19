"""Application + match-result models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    DRY_RUN = "dry_run"          # prepared but not actually submitted
    SUBMITTED = "submitted"
    REJECTED_BY_GUARDRAIL = "rejected_by_guardrail"
    RATE_LIMITED = "rate_limited"
    INTERVIEW = "interview"
    OFFER = "offer"
    CLOSED = "closed"
    ERROR = "error"


class MatchResult(BaseModel):
    """Output of the matching agent for a single job."""

    job_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    skill_score: float = 0.0
    experience_score: float = 0.0
    location_score: float = 0.0
    goal_score: float = 0.0
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    rationale: str = ""


class Application(BaseModel):
    """A tracked application record."""

    id: str
    user_id: str
    job_id: str
    status: ApplicationStatus = ApplicationStatus.DRAFT
    platform: str = ""
    resume_ref: Optional[str] = None
    cover_letter_ref: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
