"""Cover Letter Agent: tailored letter, factually grounded in the CV."""
from __future__ import annotations

from .base import BaseAgent
from ..guardrails.factual_accuracy import check_factual_accuracy
from ..models.documents import GeneratedCoverLetter
from ..models.job import Job
from ..models.profile import UserProfile
from ..tools import cover_letter


class CoverLetterAgent(BaseAgent):
    name = "CoverLetterAgent"
    instructions = "Write a concise, tailored cover letter grounded only in the candidate's CV."

    def run(self, profile: UserProfile, job: Job) -> GeneratedCoverLetter:
        letter = cover_letter.generate_cover_letter(profile, job)
        factual = check_factual_accuracy(letter.body, profile)
        if not factual.passed:
            self.log.warning("Cover letter factual guardrail tripped: %s", factual.issues)
            # Regenerate with a neutral skill phrase to avoid unsupported claims.
            letter.body = letter.body.replace(
                ", ".join(profile.skills[:5]), "the core technologies for this role"
            )
            letter.word_count = len(letter.body.split())
        return letter
