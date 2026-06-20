"""End-to-end pipeline runner."""
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
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.orchestrator = CareerOrchestrator(settings=self.settings)
        self.profile_repo = ProfileRepository()

    def build_profile(self, user_id: str, cv_text: str, career_goals: str = "") -> UserProfile:
        scrubbed, redactions = scrub_pii(cv_text)
        if redactions:
            log.info("PII guardrail redacted %d sensitive token(s) before parsing.", redactions)
        profile = cv_parser.parse_cv(user_id, scrubbed, career_goals=career_goals)
        self.profile_repo.save(profile)
        return profile

    def run(
        self,
        profile: UserProfile,
        request: JobSearchRequest,
        top_k: int = 5,
        auto_apply: bool = True,
        apply_min_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        threshold = self.settings.auto_apply_min_score if apply_min_score is None else apply_min_score
        t0 = time.time()
        ctx = ProfileContext(user_id=profile.user_id, profile=profile)
        orch = self.orchestrator

        completeness = check_profile_completeness(profile)
        if not completeness.passed:
            log.warning("Profile completeness issues: %s", completeness.issues)
        ctx.record_step("CareerOrchestrator", "profile prepared",
                        completeness_issues=completeness.issues)

        jobs = orch.scraping.run(request)
        ctx.job_queue = [j.id for j in jobs]
        ctx.record_step(orch.scraping.name, f"scraped {len(jobs)} jobs")

        verified = orch.verification.run(jobs)
        ctx.record_step(orch.verification.name, f"{len(verified)} verified")

        ranked = orch.matching.run(profile, verified, top_k=top_k)
        ctx.match_scores = {job.id: result.score for job, result in ranked}
        ctx.record_step(orch.matching.name, f"ranked top {len(ranked)}")

        recommendations: List[Dict[str, Any]] = []
        for job, match in ranked:
            resume = orch.resume.run(profile, job)
            letter = orch.cover_letter.run(profile, job)

            application = None
            if auto_apply and match.score >= threshold:
                application = orch.application.run(
                    profile.user_id, job, resume.plain_text, letter.body, match_score=match.score
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

        return {
            "user_id": profile.user_id,
            "query": request.query,
            "jobs_scraped": len(jobs),
            "jobs_verified": len(verified),
            "recommendations": recommendations,
            "agent_chain": ctx.agent_chain,
            "elapsed_s": round(time.time() - t0, 3),
        }

    def auto_apply(
        self,
        profile: UserProfile,
        request: JobSearchRequest,
        min_score: Optional[float] = None,
        max_applications: int = 10,
        top_k: int = 25,
    ) -> Dict[str, Any]:
        """Scrape -> verify -> match -> auto-submit to jobs above min_score
        (up to max_applications), honoring verification, ATS, and rate limits."""
        threshold = self.settings.auto_apply_min_score if min_score is None else min_score
        t0 = time.time()
        orch = self.orchestrator

        jobs = orch.scraping.run(request)
        verified = orch.verification.run(jobs)
        ranked = orch.matching.run(profile, verified, top_k=top_k)

        applied: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        submitted_count = 0

        for job, match in ranked:
            if len(applied) >= max_applications:
                skipped.append({"job": job.model_dump(mode="json"), "reason": "per-run cap reached"})
                continue
            if match.score < threshold:
                skipped.append({
                    "job": job.model_dump(mode="json"),
                    "reason": f"below threshold ({match.score:.2f} < {threshold:.2f})",
                })
                continue

            resume = orch.resume.run(profile, job)
            letter = orch.cover_letter.run(profile, job)
            application = orch.application.run(
                profile.user_id, job, resume.plain_text, letter.body, match_score=match.score
            )

            if application.status.value in ("submitted", "dry_run"):
                submitted_count += 1

            applied.append({
                "job": job.model_dump(mode="json"),
                "match": match.model_dump(mode="json"),
                "application": application.model_dump(mode="json"),
            })

        return {
            "user_id": profile.user_id,
            "query": request.query,
            "jobs_scraped": len(jobs),
            "jobs_verified": len(verified),
            "min_score": threshold,
            "max_applications": max_applications,
            "submitted_count": submitted_count,
            "dry_run": not self.settings.allow_live_apply,
            "daily_cap": self.settings.daily_application_cap,
            "applied": applied,
            "skipped": skipped,
            "elapsed_s": round(time.time() - t0, 3),
        }
