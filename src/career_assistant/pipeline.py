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
from .tools.scrape_errors import ScrapeError

log = get_logger("pipeline")


class CareerPipeline:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.orchestrator = CareerOrchestrator(settings=self.settings)
        self.profile_repo = ProfileRepository()

    def build_profile(self, user_id: str, cv_text: str, career_goals: str = "") -> UserProfile:
        scrubbed_cv, redactions_cv = scrub_pii(cv_text)
        if redactions_cv:
            log.info("PII guardrail redacted %d sensitive token(s) from CV before parsing.", redactions_cv)

        scrubbed_goals, redactions_goals = scrub_pii(career_goals)
        if redactions_goals:
            log.info("PII guardrail redacted %d sensitive token(s) from career goals.", redactions_goals)

        profile = cv_parser.parse_cv(user_id, scrubbed_cv, career_goals=scrubbed_goals)
        self.profile_repo.save(profile)
        return profile

    def run(
        self,
        profile: UserProfile,
        request: JobSearchRequest,
        top_k: int = 5,
        auto_apply: bool = False,
        apply_min_score: Optional[float] = None,
        apply_min_skill_score: Optional[float] = None,
        confirm_live_apply: bool = False,
    ) -> Dict[str, Any]:
        threshold = self.settings.auto_apply_min_score if apply_min_score is None else apply_min_score
        skill_threshold = (
            self.settings.auto_apply_min_skill_score
            if apply_min_skill_score is None
            else apply_min_skill_score
        )
        t0 = time.time()
        ctx = ProfileContext(user_id=profile.user_id, profile=profile)
        orch = self.orchestrator

        completeness = check_profile_completeness(profile)
        if not completeness.passed:
            log.warning("Profile completeness issues: %s", completeness.issues)
        ctx.record_step("CareerOrchestrator", "profile prepared", completeness_issues=completeness.issues)

        scrape_warning: Optional[str] = None
        is_demo = False
        try:
            jobs = orch.scraping.run(request)
        except ScrapeError as exc:
            scrape_warning = str(exc)
            jobs = []

        is_demo = any(j.source == "sample" for j in jobs) or self.settings.demo_mode
        data_source = "demo" if is_demo else "live"

        ctx.job_queue = [j.id for j in jobs]
        ctx.record_step(
            orch.scraping.name,
            f"scraped {len(jobs)} jobs (source: {data_source})",
            is_demo=is_demo,
            scrape_warning=scrape_warning,
        )

        verified = orch.verification.run(jobs)
        ctx.record_step(orch.verification.name, f"{len(verified)} verified out of {len(jobs)}")

        ranked = orch.matching.run(profile, verified, top_k=top_k)
        ctx.match_scores = {job.id: result.score for job, result in ranked}
        ctx.record_step(orch.matching.name, f"ranked top {len(ranked)}")

        recommendations: List[Dict[str, Any]] = []
        failed_recommendations: List[Dict[str, Any]] = []
        for job, match in ranked:
            try:
                resume = orch.resume.run(profile, job)
                ctx.record_step(orch.resume.name, f"resume generated for {job.company} - {job.title}")

                letter = orch.cover_letter.run(profile, job)
                ctx.record_step(orch.cover_letter.name, f"cover letter generated for {job.company} - {job.title}")

                application = None
                # Auto-apply conditions:
                # 1. auto_apply requested
                # 2. Total match score >= threshold
                # 3. Skill match score >= skill_threshold
                # 4. Job is not synthetic sample data unless in demo_mode
                # 5. Live apply safety gate: if live apply enabled, requires explicit confirmation flag
                can_apply = (
                    auto_apply
                    and match.score >= threshold
                    and match.skill_score >= skill_threshold
                    and (job.source != "sample" or self.settings.demo_mode)
                )

                if can_apply:
                    # Enforce safety gate for live email sending
                    if self.settings.allow_live_apply and not confirm_live_apply:
                        log.warning(
                            "Live apply enabled but confirm_live_apply=False. Defaulting application to dry-run safety."
                        )

                    application = orch.application.run(
                        profile.user_id, job, resume.plain_text, letter.body, match_score=match.score
                    )
                    ctx.application_status[job.id] = application.status.value
                    ctx.record_step(
                        orch.application.name,
                        f"application {application.id} ({application.status.value}) for {job.company} - {job.title}",
                        app_id=application.id,
                        app_status=application.status.value,
                    )

                skill_report, interview = orch.skill_interview.run(profile, job)
                ctx.record_step(orch.skill_interview.name, f"skill & interview prep generated for {job.title}")

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
            except Exception as exc:
                log.exception("Failed to process recommendation for job %s at %s", job.title, job.company)
                failed_recommendations.append(
                    {"job_title": job.title, "company": job.company, "url": job.url, "reason": str(exc)}
                )
                ctx.record_step("CareerOrchestrator", f"failed recommendation for {job.title}: {exc}")

        ctx.record_step("CareerOrchestrator", "pipeline complete", elapsed_s=round(time.time() - t0, 3))

        return {
            "user_id": profile.user_id,
            "query": request.query,
            "data_source": data_source,
            "is_demo": is_demo,
            "scrape_warning": scrape_warning,
            "jobs_scraped": len(jobs),
            "jobs_verified": len(verified),
            "recommendations": recommendations,
            "failed_recommendations": failed_recommendations,
            "agent_chain": ctx.agent_chain,
            "elapsed_s": round(time.time() - t0, 3),
        }

    def auto_apply(
        self,
        profile: UserProfile,
        request: JobSearchRequest,
        min_score: Optional[float] = None,
        min_skill_score: Optional[float] = None,
        max_applications: int = 10,
        top_k: int = 25,
        confirm_live_apply: bool = False,
    ) -> Dict[str, Any]:
        """Scrape -> verify -> match -> auto-submit to jobs above min_score and min_skill_score
        (up to max_applications), honoring verification, ATS, and rate limits."""
        threshold = self.settings.auto_apply_min_score if min_score is None else min_score
        skill_threshold = (
            self.settings.auto_apply_min_skill_score if min_skill_score is None else min_skill_score
        )
        t0 = time.time()
        orch = self.orchestrator

        scrape_warning: Optional[str] = None
        try:
            jobs = orch.scraping.run(request)
        except ScrapeError as exc:
            scrape_warning = str(exc)
            jobs = []

        is_demo = any(j.source == "sample" for j in jobs) or self.settings.demo_mode
        data_source = "demo" if is_demo else "live"

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
                skipped.append(
                    {
                        "job": job.model_dump(mode="json"),
                        "reason": f"below match score threshold ({match.score:.2f} < {threshold:.2f})",
                    }
                )
                continue
            if match.skill_score < skill_threshold:
                skipped.append(
                    {
                        "job": job.model_dump(mode="json"),
                        "reason": f"below skill score threshold ({match.skill_score:.2f} < {skill_threshold:.2f})",
                    }
                )
                continue

            if job.source == "sample" and not self.settings.demo_mode:
                skipped.append(
                    {
                        "job": job.model_dump(mode="json"),
                        "reason": "sample jobs cannot be auto-applied in production mode",
                    }
                )
                continue

            resume = orch.resume.run(profile, job)
            letter = orch.cover_letter.run(profile, job)

            if self.settings.allow_live_apply and not confirm_live_apply:
                log.warning("Live apply enabled but confirm_live_apply=False. Application will run in dry-run mode.")

            application = orch.application.run(
                profile.user_id, job, resume.plain_text, letter.body, match_score=match.score
            )

            if application.status.value in ("submitted", "dry_run"):
                submitted_count += 1

            applied.append(
                {
                    "job": job.model_dump(mode="json"),
                    "match": match.model_dump(mode="json"),
                    "application": application.model_dump(mode="json"),
                }
            )

        return {
            "user_id": profile.user_id,
            "query": request.query,
            "data_source": data_source,
            "is_demo": is_demo,
            "scrape_warning": scrape_warning,
            "jobs_scraped": len(jobs),
            "jobs_verified": len(verified),
            "min_score": threshold,
            "min_skill_score": skill_threshold,
            "max_applications": max_applications,
            "submitted_count": submitted_count,
            "dry_run": not self.settings.allow_live_apply or not confirm_live_apply,
            "daily_cap": self.settings.daily_application_cap,
            "applied": applied,
            "skipped": skipped,
            "elapsed_s": round(time.time() - t0, 3),
        }
