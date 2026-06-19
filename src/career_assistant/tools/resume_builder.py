"""Resume generation tool.

Reorders/highlights existing CV content to match a job. CRITICAL: it never introduces
skills or experience absent from the profile - enforced again by the factual-accuracy
guardrail downstream.
"""
from __future__ import annotations

from typing import List

from ..models.documents import GeneratedResume
from ..models.job import Job
from ..models.profile import UserProfile
from .match_score import calculate_match_score


def generate_resume(profile: UserProfile, job: Job) -> GeneratedResume:
    match = calculate_match_score(profile, job)
    # Highlight only skills the candidate actually has that the job wants.
    highlighted = match.matched_skills or profile.skills[:8]

    summary = _summary(profile, job, highlighted)
    sections = _sections(profile, job, highlighted)
    plain = summary + "\n\n" + "\n".join(sections)

    return GeneratedResume(
        job_id=job.id,
        summary=summary,
        highlighted_skills=highlighted,
        sections=sections,
        plain_text=plain,
    )


def _summary(profile: UserProfile, job: Job, highlighted: List[str]) -> str:
    name = profile.full_name or "Candidate"
    years = f"{profile.years_experience:g}+ years" if profile.years_experience else "experienced"
    skills = ", ".join(highlighted[:6]) if highlighted else "relevant technologies"
    return (
        f"{name} - {years} professional targeting the {job.title} role at "
        f"{job.company or 'the company'}. Core strengths: {skills}."
    )


def _sections(profile: UserProfile, job: Job, highlighted: List[str]) -> List[str]:
    sections = []
    if highlighted:
        sections.append("SKILLS\n- " + "\n- ".join(highlighted))
    if profile.titles:
        sections.append("EXPERIENCE\n- " + "\n- ".join(profile.titles))
    if profile.summary:
        sections.append("PROFILE\n" + profile.summary)
    if profile.career_goals:
        sections.append("OBJECTIVE\n" + profile.career_goals)
    return sections
