"""Job and search-request models."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class JobSearchRequest(BaseModel):
    """A normalized request for the scraping agent."""

    query: str = Field(..., min_length=1, description="Search term, e.g. 'python developer'.")
    location: str = Field(default="Remote")
    sites: List[str] = Field(default_factory=lambda: ["indeed"])
    results_wanted: int = Field(default=25, ge=1, le=1000)  # Indeed/JobSpy hard cap is 1000
    hours_old: Optional[int] = Field(default=None, ge=1, description="Only jobs posted within N hours.")
    is_remote: bool = False
    # any | remote | hybrid | onsite - applied as a post-scrape filter.
    work_arrangement: str = Field(default="any", description="any | remote | hybrid | onsite")
    country: str = Field(default="USA", description="JobSpy 'country_indeed' value.")

    @field_validator("results_wanted")
    @classmethod
    def _cap(cls, v: int) -> int:
        return min(v, 1000)

    @field_validator("work_arrangement")
    @classmethod
    def _norm_arrangement(cls, v: str) -> str:
        val = (v or "any").strip().lower()
        return val if val in {"any", "remote", "hybrid", "onsite"} else "any"


class Job(BaseModel):
    """A single normalized job posting (board-agnostic)."""

    id: str = Field(default="", description="Stable hash id; auto-derived if empty.")
    source: str = "unknown"
    title: str
    company: str = ""
    location: str = ""
    description: str = ""
    url: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    is_remote: bool = False
    date_posted: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    # Set by the verification agent.
    verified: bool = False
    verification_notes: List[str] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:  # pydantic v2 hook
        if not self.id:
            seed = f"{self.source}|{self.company}|{self.title}|{self.url or self.location}".lower()
            object.__setattr__(self, "id", hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16])

    @property
    def dedupe_key(self) -> str:
        """Key used to detect duplicate postings across boards."""
        return f"{self.company.strip().lower()}::{self.title.strip().lower()}"

    @property
    def salary_text(self) -> str:
        if self.salary_min and self.salary_max:
            cur = self.currency or ""
            return f"{cur}{self.salary_min:,.0f}-{cur}{self.salary_max:,.0f}".strip()
        return "unspecified"
