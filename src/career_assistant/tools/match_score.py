"""Explainable, weighted job-match scoring.

Weights (sum to 1.0):
  skills 0.45, experience 0.25, location 0.15, goal alignment 0.15
"""
from __future__ import annotations

import re
from typing import List, Tuple

from ..models.application import MatchResult
from ..models.job import Job
from ..models.profile import UserProfile

W_SKILLS = 0.45
W_EXPERIENCE = 0.25
W_LOCATION = 0.15
W_GOAL = 0.15

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]*")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _experience_required(description: str) -> float:
    m = re.search(r"(\d+)\+?\s*years?", description or "", re.IGNORECASE)
    return float(m.group(1)) if m else 0.0


def _skill_overlap(profile: UserProfile, job: Job) -> Tuple[float, List[str], List[str]]:
    job_tokens = _tokens(job.title) | _tokens(job.description)
    matched = sorted(s for s in profile.skills if s.lower() in job_tokens)
    # Skills the job mentions that the profile lacks (limited to known skill-like words).
    profile_skills = profile.skills_lower
    missing = sorted(
        {
            tok
            for tok in job_tokens
            if tok in _COMMON_SKILLS and tok not in profile_skills
        }
    )
    denom = max(len(profile.skills), 1)
    score = min(len(matched) / denom, 1.0) if profile.skills else 0.0
    return score, matched, missing


_COMMON_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "django", "fastapi",
    "flask", "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
    "postgresql", "mysql", "mongodb", "redis", "pytorch", "tensorflow",
    "mlops", "spark", "kafka", "graphql", "go", "rust", "c++", "sql",
}


def _location_score(profile: UserProfile, job: Job) -> float:
    if job.is_remote and profile.remote_ok:
        return 1.0
    job_loc = (job.location or "").lower()
    for pref in profile.locations_preferred:
        if pref.lower() in job_loc or job_loc in pref.lower():
            return 1.0
    if "remote" in job_loc and profile.remote_ok:
        return 1.0
    return 0.3 if job_loc else 0.5


def _experience_score(profile: UserProfile, job: Job) -> float:
    required = _experience_required(job.description)
    if required <= 0:
        return 0.7
    if profile.years_experience >= required:
        return 1.0
    return max(profile.years_experience / required, 0.0)


def _goal_score(profile: UserProfile, job: Job) -> float:
    goal_tokens = _tokens(profile.career_goals) | {t.lower() for t in profile.titles}
    if not goal_tokens:
        return 0.6
    title_tokens = _tokens(job.title)
    overlap = goal_tokens & title_tokens
    return min(0.5 + 0.5 * len(overlap), 1.0)


def calculate_match_score(profile: UserProfile, job: Job) -> MatchResult:
    skill_score, matched, missing = _skill_overlap(profile, job)
    exp_score = _experience_score(profile, job)
    loc_score = _location_score(profile, job)
    goal_score = _goal_score(profile, job)

    total = (
        W_SKILLS * skill_score
        + W_EXPERIENCE * exp_score
        + W_LOCATION * loc_score
        + W_GOAL * goal_score
    )
    rationale = (
        f"skills={skill_score:.2f}, experience={exp_score:.2f}, "
        f"location={loc_score:.2f}, goals={goal_score:.2f}"
    )
    return MatchResult(
        job_id=job.id,
        score=round(total, 4),
        skill_score=round(skill_score, 4),
        experience_score=round(exp_score, 4),
        location_score=round(loc_score, 4),
        goal_score=round(goal_score, 4),
        matched_skills=matched,
        missing_skills=missing,
        rationale=rationale,
    )
