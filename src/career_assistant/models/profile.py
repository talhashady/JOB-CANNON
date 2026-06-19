"""User profile and session-context models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, EmailStr, field_validator


class UserProfile(BaseModel):
    """The candidate profile derived from a CV plus stated preferences."""

    user_id: str
    full_name: str = ""
    email: Optional[str] = None  # kept loose; scrubbed before model calls
    headline: str = ""
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    years_experience: float = 0.0
    titles: List[str] = Field(default_factory=list)
    locations_preferred: List[str] = Field(default_factory=list)
    remote_ok: bool = True
    career_goals: str = ""
    raw_cv_text: str = ""

    @field_validator("skills", "titles", "locations_preferred")
    @classmethod
    def _normalize(cls, v: List[str]) -> List[str]:
        seen, out = set(), []
        for item in v:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(item.strip())
        return out

    @property
    def skills_lower(self) -> set[str]:
        return {s.lower() for s in self.skills}


class ProfileContext(BaseModel):
    """Session object persisted across the pipeline (mirrors SDK Sessions).

    State keys map directly to the blueprint: user_id, profile_data, job_queue,
    match_scores, application_status, agent_chain, timestamps.
    """

    user_id: str
    profile: UserProfile
    job_queue: List[str] = Field(default_factory=list)
    match_scores: Dict[str, float] = Field(default_factory=dict)
    application_status: Dict[str, str] = Field(default_factory=dict)
    agent_chain: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def record_step(self, agent: str, summary: str, **extra: Any) -> None:
        """Append an entry to the audit trail (used for tracing/observability)."""
        self.agent_chain.append(
            {
                "agent": agent,
                "summary": summary,
                "at": datetime.utcnow().isoformat(),
                **extra,
            }
        )
        self.updated_at = datetime.utcnow()
