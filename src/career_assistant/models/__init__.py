"""Pydantic domain models."""
from .job import Job, JobSearchRequest
from .profile import UserProfile, ProfileContext
from .application import Application, ApplicationStatus, MatchResult
from .documents import GeneratedResume, GeneratedCoverLetter, SkillGapReport, InterviewPrep

__all__ = [
    "Job",
    "JobSearchRequest",
    "UserProfile",
    "ProfileContext",
    "Application",
    "ApplicationStatus",
    "MatchResult",
    "GeneratedResume",
    "GeneratedCoverLetter",
    "SkillGapReport",
    "InterviewPrep",
]
