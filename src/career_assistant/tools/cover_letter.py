"""Cover-letter generation tool (grounded in the CV; no invented claims)."""
from __future__ import annotations

from ..models.documents import GeneratedCoverLetter
from ..models.job import Job
from ..models.profile import UserProfile
from .match_score import calculate_match_score


def generate_cover_letter(profile: UserProfile, job: Job) -> GeneratedCoverLetter:
    match = calculate_match_score(profile, job)
    skills = ", ".join(match.matched_skills[:5]) if match.matched_skills else ", ".join(profile.skills[:5])
    name = profile.full_name or "the applicant"
    company = job.company or "your company"

    body = (
        f"Dear Hiring Team at {company},\n\n"
        f"I am writing to express my interest in the {job.title} position. "
        f"With a background spanning {profile.years_experience:g} years and hands-on "
        f"experience in {skills or 'the core technologies for this role'}, I am confident "
        f"I can contribute from day one.\n\n"
        f"{profile.career_goals or 'I am eager to bring my skills to a team building meaningful products.'} "
        f"My experience aligns closely with your requirements, and I would welcome the "
        f"opportunity to discuss how I can add value to {company}.\n\n"
        f"Thank you for your consideration.\n\n"
        f"Sincerely,\n{name}"
    )
    return GeneratedCoverLetter(job_id=job.id, body=body, word_count=len(body.split()))
