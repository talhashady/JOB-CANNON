"""Resume Agent: builds an ATS-safe, factually-grounded resume."""
from __future__ import annotations

from .base import BaseAgent
from ..guardrails.ats_validator import validate_ats
from ..guardrails.factual_accuracy import check_factual_accuracy
from ..models.documents import GeneratedResume
from ..models.job import Job
from ..models.profile import UserProfile
from ..tools import resume_builder


class ResumeAgent(BaseAgent):
    name = "ResumeOptimizationAgent"
    instructions = (
        "Reorganize and highlight CV content to match job requirements. NEVER invent "
        "skills or experience. Ensure ATS compatibility."
    )

    def run(self, profile: UserProfile, job: Job) -> GeneratedResume:
        resume = resume_builder.generate_resume(profile, job)

        # Output guardrails.
        factual = check_factual_accuracy(resume.plain_text, profile)
        ats = validate_ats(resume.plain_text)
        resume.ats_passed = ats.passed
        resume.ats_issues = ats.issues

        if not factual.passed:
            # Strip the offending content rather than ship a fabrication.
            self.log.warning("Factual guardrail tripped: %s", factual.issues)
            resume.highlighted_skills = [s for s in resume.highlighted_skills if s.lower() in profile.skills_lower]
            resume.sections = [s for s in resume.sections if not s.startswith("SKILLS")]
            if resume.highlighted_skills:
                resume.sections.insert(0, "SKILLS\n- " + "\n- ".join(resume.highlighted_skills))
            resume.plain_text = resume.summary + "\n\n" + "\n".join(resume.sections)
            resume.ats_issues.append("Factual guardrail removed unsupported skills.")
        return resume
