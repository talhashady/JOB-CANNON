"""Generated-document models: resume, cover letter, skill gap, interview prep."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class GeneratedResume(BaseModel):
    job_id: str
    summary: str = ""
    highlighted_skills: List[str] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)
    plain_text: str = ""
    ats_passed: bool = True
    ats_issues: List[str] = Field(default_factory=list)


class GeneratedCoverLetter(BaseModel):
    job_id: str
    body: str = ""
    word_count: int = 0


class SkillGapReport(BaseModel):
    job_id: str
    missing_skills: List[str] = Field(default_factory=list)
    learning_roadmap: List[str] = Field(default_factory=list)
    estimated_weeks: int = 0


class InterviewPrep(BaseModel):
    job_id: str
    technical_questions: List[str] = Field(default_factory=list)
    behavioral_questions: List[str] = Field(default_factory=list)
    tips: List[str] = Field(default_factory=list)
