"""Input guardrail: ensure a profile is complete enough before matching."""
from __future__ import annotations

from .base import GuardResult
from ..models.profile import UserProfile

MIN_SKILLS = 3


def check_profile_completeness(profile: UserProfile) -> GuardResult:
    issues = []
    if len(profile.skills) < MIN_SKILLS:
        issues.append(f"Profile lists {len(profile.skills)} skill(s); at least {MIN_SKILLS} recommended.")
    if profile.years_experience <= 0:
        issues.append("No years of experience detected.")
    if not profile.titles:
        issues.append("No job titles detected in the CV.")
    if not profile.raw_cv_text.strip():
        issues.append("Empty CV text.")
    return GuardResult(passed=len(issues) == 0, issues=issues)
