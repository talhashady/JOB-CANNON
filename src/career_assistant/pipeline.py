"""End-to-end pipeline runner.

Ties the orchestrator + specialist agents together into the blueprint's pipeline:
scrape -> verify -> match -> (per top job) resume + cover letter -> apply (dry-run)
-> track -> skill gap + interview prep. Maintains a ProfileContext throughout.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .agents.orchestrator import CareerOrchestrator
from .config import Settings, get_settings
from .guardrails.pii import scrub_pii
from .guardrails.profile_completeness import check_profile_completeness
from .logging_config import get_logger
from .models.job import JobSearchRequest
from .models.profile import ProfileContext, UserProfile
from .storage.repositories import ProfileRepository
from .tools import cv_parser

log = get_logger("pipeline")


class CareerPipeline:
    """High-level facade. `run` executes the full journey for one user/search."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.orchestrator = CareerOrchestrator(settings=self.settings)
        self.profile_repo = ProfileRepository()

    # -- profile construction -------------------------------------------------
    def build_profile(self, user_id: str, cv_text: str, career_goals: str = "") -> UserProfile:
        """Scrub PII, then parse the CV into a profile (input guardrail first)."""
        scrubbed, redactions = scrub_pii(cv_text)
        if redactions:
            log.info("PII guardrail redacted %d sensitive token(s) before parsing.", redactions)
        profile = cv_parser.parse_cv(user_id, scrubbed, career_goals=career_goals)
        self.profile_repo.save(profile)
        return profile

    # -- full run -------------------------------------------------------------
    def run(
        self,
        profile: UserProfile,
        request: JobSearchRequest,
        top_k: int = 5,
        auto_apply: bool = True,
    ) -> Dict[str, Any]:
        t0 = time.time()
        ctx = ProfileContext(user_id=profile.user_id, profile=profile)
        orch = self.orchestrator

        # Input guardrail: profile completeness (warn, don't hard-fail).
        completeness = check_profile_completeness(profile)
        if not completeness.passed:
            log.warning("Profile completeness issues: %s", completeness.issues)
        ctx.record_step("CareerOrchestrator", "profile prepared",
                        completeness_issues=completeness.issues)

        # 1. Scrape
        jobs = orch.scraping.run(request)
        ctx.job_queue = [j.id for j in jobs]
        ctx.record_step(orch.scraping.name, f"scraped {len(jobs)} jobs")

        # 2. Verify
        verified = orch.verification.run(jobs)
        ctx.record_step(orch.verification.name, f"{len(verified)} verified")

        # 3. Match (only verified jobs are ranked)
        ranked = orch.matching.run(profile, verified, top_k=top_k)
        ctx.match_scores = {job.id: result.score for job, result in ranked}
        ctx.record_step(orch.matching.name, f"ranked top {len(ranked)}")

        # 4-7. Per top job: documents -> apply -> track -> skills/interview
        recommendations: List[Dict[str, Any]] = []
        for job, match in ranked:
            resume = orch.resume.run(profile, job)
            letter = orch.cover_letter.run(profile, job)

            application = None
            if auto_apply:
                application = orch.application.run(
                    profile.user_id, job, resume.plain_text, letter.body
                )
                ctx.application_status[job.id] = application.status.value

            skill_report, interview = orch.skill_interview.run(profile, job)

            recommendations.append(
                {
                    "job": job.model_dump(mode="json"),
                    "match": match.model_dump(mode="json"),
                    "resume": resume.model_dump(mode="json"),
                    "cover_letter": letter.model_dump(mode="json"),
                    "application": application.model_dump(mode="json") if application else None,
                    "skill_gap": skill_report.model_dump(mode="json"),
                    "interview_prep": interview.model_dump(mode="json"),
                }
            )

        ctx.record_step("CareerOrchestrator", "pipeline complete",
                        elapsed_s=round(time.time() - t0, 3))
        log.info("Pipeline finished in %.2fs with %d recommendations.",
                 time.time() - t0, len(recommendations))

        return {
            "user_id": profile.user_id,
            "query": request.query,
            "jobs_scraped": len(jobs),
            "jobs_verified": len(verified),
            "recommendations": recommendations,
            "agent_chain": ctx.agent_chain,
            "elapsed_s": round(time.time() - t0, 3),
        }
