"""Cover Letter Agent: LLM-enhanced when a key is set, grounded in the CV."""
from __future__ import annotations

from .base import BaseAgent
from ..guardrails.factual_accuracy import check_factual_accuracy
from ..models.documents import GeneratedCoverLetter
from ..models.job import Job
from ..models.profile import UserProfile
from ..tools import cover_letter
from ..tools.match_score import calculate_match_score

_SYSTEM = (
    "You are an expert career writer. Write a concise, compelling, professional cover letter. "
    "Rules: ground every claim ONLY in the candidate facts provided; never invent skills, "
    "employers, metrics, or dates. Use a confident, warm, human tone with no cliches and no "
    "buzzword stuffing. Use business-letter format, 4 short paragraphs, about 250-320 words. "
    "End with 'Sincerely,' followed by the candidate's name."
)


class CoverLetterAgent(BaseAgent):
    name = "CoverLetterAgent"
    instructions = "Write a concise, tailored cover letter grounded only in the candidate's CV."

    def run(self, profile: UserProfile, job: Job) -> GeneratedCoverLetter:
        # Deterministic professional letter as baseline + guaranteed fallback.
        letter = cover_letter.generate_cover_letter(profile, job)

        if self.llm.enabled:
            match = calculate_match_score(profile, job)
            facts = (
                f"Candidate name: {profile.full_name or 'N/A'}\n"
                f"Years of experience: {profile.years_experience:g}\n"
                f"Past/current titles: {', '.join(profile.titles) or 'N/A'}\n"
                f"Skills: {', '.join(profile.skills) or 'N/A'}\n"
                f"Matched skills for this job: {', '.join(match.matched_skills) or 'N/A'}\n"
                f"Career goals: {profile.career_goals or 'N/A'}\n\n"
                f"Job title: {job.title}\nCompany: {job.company}\n"
                f"Job description: {(job.description or '')[:1500]}"
            )
            user = "Write the cover letter using ONLY these facts. Do not fabricate.\n\n" + facts
            generated = self.llm.complete(model=self.model, system=_SYSTEM, user=user)
            if generated and len(generated.split()) > 80:
                candidate = GeneratedCoverLetter(
                    job_id=job.id, subject=letter.subject,
                    body=generated.strip(), word_count=len(generated.split()),
                )
                if check_factual_accuracy(candidate.body, profile).passed:
                    return candidate
                self.log.warning("LLM cover letter failed factual guardrail; using template.")

        factual = check_factual_accuracy(letter.body, profile)
        if not factual.passed:
            self.log.warning("Cover letter factual guardrail tripped: %s", factual.issues)
            letter.body = letter.body.replace(
                ", ".join(profile.skills[:5]), "the core technologies for this role"
            )
            letter.word_count = len(letter.body.split())
        return letter
