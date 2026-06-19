"""Output guardrail: resumes/cover letters may not introduce skills absent from the CV.

We tokenize the generated document and check any known-skill token against the profile's
skill set. If a claimed skill isn't backed by the profile, the guard fails.
"""
from __future__ import annotations

import re
from typing import Iterable

from .base import GuardResult
from ..models.profile import UserProfile

_KNOWN_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "vue", "angular",
    "django", "fastapi", "flask", "aws", "gcp", "azure", "docker", "kubernetes",
    "terraform", "postgresql", "mysql", "mongodb", "redis", "pytorch",
    "tensorflow", "mlops", "spark", "kafka", "graphql", "go", "rust", "c++", "sql",
}

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]*")


def _skill_tokens(text: str) -> Iterable[str]:
    for tok in _TOKEN_RE.findall(text or ""):
        low = tok.lower()
        if low in _KNOWN_SKILLS:
            yield low


def check_factual_accuracy(document_text: str, profile: UserProfile) -> GuardResult:
    allowed = profile.skills_lower
    fabricated = sorted({tok for tok in _skill_tokens(document_text) if tok not in allowed})
    if fabricated:
        return GuardResult(
            passed=False,
            issues=[f"Document claims skills not in the CV: {', '.join(fabricated)}"],
        )
    return GuardResult(passed=True)
