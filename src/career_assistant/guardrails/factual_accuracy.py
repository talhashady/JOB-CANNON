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


def check_factual_accuracy(
    document_text: str,
    profile: UserProfile,
    job_title: str = "",
    company: str = "",
) -> GuardResult:
    """Validate that the document does not claim skills not present in the profile.

    Before checking, we strip out greetings, closings, headers, and direct references to
    the job title or company name to avoid false positives (e.g. matching a skill word that
    appears in the job title itself).
    """
    allowed = profile.skills_lower

    # Clean the text to avoid false positives on metadata/headers/greetings
    clean_text = document_text

    # Strip headers/subject lines starting with Re:, Subject:, etc.
    clean_text = re.sub(r"(?im)^\s*(?:re|subject|ref|date|to|from):?.*$", "", clean_text)

    # Strip greetings and closings
    clean_text = re.sub(r"(?i)\b(?:dear|sincerely|respectfully|best regards|regards|thank you)\b.*", "", clean_text)

    # Strip exact job title and company references
    if job_title:
        clean_text = re.sub(re.escape(job_title), " ", clean_text, flags=re.IGNORECASE)
        # Handle case where job title has dynamic formatting
        words = job_title.split()
        if len(words) > 1:
            for word in words:
                if word.lower() in _KNOWN_SKILLS:
                    # Clean up isolated instances of job title parts if they are skill words
                    clean_text = re.sub(rf"(?i)\b{re.escape(word)}\b\s+(?:role|position|job|posting|opportunity)", " ", clean_text)

    if company:
        clean_text = re.sub(re.escape(company), " ", clean_text, flags=re.IGNORECASE)

    fabricated = sorted({tok for tok in _skill_tokens(clean_text) if tok not in allowed})
    if fabricated:
        return GuardResult(
            passed=False,
            issues=[f"Document claims skills not in the CV: {', '.join(fabricated)}"],
        )
    return GuardResult(passed=True)
