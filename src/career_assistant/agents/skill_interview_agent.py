"""Skill-Gap & Interview Agent: roadmap + mock interview."""
from __future__ import annotations

from typing import Tuple

from .base import BaseAgent
from ..models.documents import InterviewPrep, SkillGapReport
from ..models.job import Job
from ..models.profile import UserProfile
from ..tools import skill_gap


class SkillInterviewAgent(BaseAgent):
    name = "SkillGapInterviewAgent"
    instructions = (
        "Identify skill gaps for the target job, propose a learning roadmap, and generate "
        "mock interview questions."
    )

    @property
    def model(self) -> str:
        # This agent benefits from the stronger model per the blueprint.
        return self.settings.orchestrator_model

    def run(self, profile: UserProfile, job: Job) -> Tuple[SkillGapReport, InterviewPrep]:
        report = skill_gap.analyze_skill_gap(profile, job)
        prep = skill_gap.build_interview_prep(profile, job)
        return report, prep
