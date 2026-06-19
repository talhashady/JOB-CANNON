"""Skill-gap analysis + interview prep tools."""
from __future__ import annotations

from typing import List

from ..models.documents import InterviewPrep, SkillGapReport
from ..models.job import Job
from ..models.profile import UserProfile
from .match_score import calculate_match_score

_LEARNING_HINTS = {
    "kubernetes": "Complete a CKA-style hands-on lab; deploy a multi-service app.",
    "aws": "Work through AWS Solutions Architect Associate core services.",
    "terraform": "Build IaC for a small stack; learn modules and remote state.",
    "pytorch": "Reimplement a small model end-to-end; cover training + inference.",
    "react": "Build a small SPA with hooks, routing, and state management.",
    "docker": "Containerize an app; write a multi-stage Dockerfile.",
    "postgresql": "Practice schema design, indexing, and query optimization.",
}


def analyze_skill_gap(profile: UserProfile, job: Job) -> SkillGapReport:
    match = calculate_match_score(profile, job)
    missing = match.missing_skills
    roadmap: List[str] = []
    for skill in missing:
        roadmap.append(_LEARNING_HINTS.get(skill, f"Build a small project using {skill}."))
    weeks = min(len(missing) * 2, 24)
    return SkillGapReport(
        job_id=job.id,
        missing_skills=missing,
        learning_roadmap=roadmap,
        estimated_weeks=weeks,
    )


def build_interview_prep(profile: UserProfile, job: Job) -> InterviewPrep:
    match = calculate_match_score(profile, job)
    tech = [f"Explain how you'd use {s} in a production system." for s in match.matched_skills[:5]]
    if not tech:
        tech = [f"Walk through your approach to a typical {job.title} problem."]
    behavioral = [
        "Tell me about a project you're most proud of.",
        "Describe a time you handled conflicting priorities.",
        f"Why are you interested in {job.company or 'this company'}?",
    ]
    tips = [
        f"Review the job description for {job.title} and map each requirement to a story.",
        "Prepare concise STAR-format answers.",
    ]
    if match.missing_skills:
        tips.append("Be ready to discuss how you'd ramp up on: " + ", ".join(match.missing_skills[:5]) + ".")
    return InterviewPrep(
        job_id=job.id,
        technical_questions=tech,
        behavioral_questions=behavioral,
        tips=tips,
    )
