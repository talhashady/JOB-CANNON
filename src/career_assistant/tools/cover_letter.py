"""Professional cover-letter generation (grounded in the CV; no invented claims)."""
from __future__ import annotations

from datetime import date

from ..models.documents import GeneratedCoverLetter
from ..models.job import Job
from ..models.profile import UserProfile
from .match_score import calculate_match_score


def _exp_phrase(years: float) -> str:
    if years <= 0:
        return "a strong foundation of hands-on project experience"
    if years < 2:
        return f"{years:g} years of focused, hands-on experience"
    if years < 6:
        return f"{years:g} years of professional experience"
    return f"over {years:g} years of senior-level experience"


def generate_cover_letter(profile: UserProfile, job: Job) -> GeneratedCoverLetter:
    match = calculate_match_score(profile, job)
    name = profile.full_name or "The Applicant"
    company = job.company or "your organization"
    title = job.title or "the open role"

    matched = match.matched_skills or profile.skills
    top_skills = ", ".join(matched[:4]) if matched else "the core technologies this role requires"
    headline_skill = matched[0] if matched else (profile.skills[0] if profile.skills else "software engineering")
    role_noun = profile.titles[0] if profile.titles else "professional"
    exp = _exp_phrase(profile.years_experience)
    today = date.today().strftime("%B %d, %Y")

    subject = f"Application for the {title} position"

    contact_bits = [b for b in [profile.email] if b]
    contact_line = "  |  ".join([name] + [str(c) for c in contact_bits])

    para1 = (
        f"I am writing to express my strong interest in the {title} role at {company}. "
        f"As a {role_noun} with {exp}, I have built my career around {headline_skill}, and the "
        f"work {company} is doing is exactly the kind of challenge where I do my best work."
    )

    para2 = (
        f"Across my experience I have delivered results using {top_skills}. I focus on shipping "
        f"reliable, well-tested solutions and partnering closely with cross-functional teams to turn "
        f"requirements into measurable outcomes. The responsibilities outlined for this position map "
        f"directly to the strengths I bring."
    )

    if profile.career_goals:
        para3 = (
            f"What draws me to {company} specifically is the opportunity to "
            f"{profile.career_goals.rstrip('.').lower()}. I am eager to contribute from day one while "
            f"continuing to grow alongside your team."
        )
    else:
        para3 = (
            f"I am drawn to {company}'s mission and would welcome the chance to contribute to your "
            f"team's goals while continuing to grow as a {role_noun}."
        )

    closing = (
        f"Thank you for considering my application. I would welcome the opportunity to discuss how my "
        f"background in {headline_skill} can help {company} succeed, and I am available for an interview "
        f"at your convenience."
    )

    body = (
        f"{today}\n\n"
        f"{company}\nRe: {subject}\n\n"
        f"Dear Hiring Manager,\n\n"
        f"{para1}\n\n{para2}\n\n{para3}\n\n{closing}\n\n"
        f"Sincerely,\n{contact_line}"
    )

    return GeneratedCoverLetter(job_id=job.id, subject=subject, body=body, word_count=len(body.split()))
