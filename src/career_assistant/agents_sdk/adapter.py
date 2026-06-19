"""Adapter that maps this repo's tools onto the OpenAI Agents SDK.

The built-in orchestrator (career_assistant.agents.orchestrator) is fully functional
and runs offline. This adapter is for teams that specifically want the official
`openai-agents` runtime (handoffs, tracing, sessions) driving the same tools.

Install with:  pip install openai-agents
Then set OPENAI_API_KEY and call run_with_sdk(...).
"""
from __future__ import annotations

from typing import Any, Optional

from ..config import get_settings
from ..logging_config import get_logger
from ..models.job import Job, JobSearchRequest
from ..models.profile import UserProfile
from ..tools import (
    company_verify,
    cover_letter,
    job_scraper,
    match_score,
    resume_builder,
    skill_gap,
)

log = get_logger("agents_sdk")


def is_available() -> bool:
    """True if the openai-agents SDK is importable."""
    try:
        import agents  # noqa: F401  (the openai-agents package)

        return True
    except Exception:
        return False


def build_orchestrator() -> Any:
    """Construct the Career Orchestrator + specialist Agents using the SDK.

    Returns the orchestrator Agent. Raises RuntimeError if the SDK is unavailable.
    """
    if not is_available():
        raise RuntimeError(
            "openai-agents is not installed. `pip install openai-agents` to use the SDK adapter."
        )

    from agents import Agent, function_tool

    settings = get_settings()

    # --- function tools (typed wrappers around our pure tools) --------------
    @function_tool
    def scrape_jobs(query: str, location: str = "Remote", sites: Optional[list[str]] = None,
                    results_wanted: int = 25, is_remote: bool = False) -> list[dict]:
        """Scrape job listings from job boards via JobSpy."""
        req = JobSearchRequest(
            query=query, location=location, sites=sites or settings.default_job_sites,
            results_wanted=results_wanted, is_remote=is_remote,
        )
        return [j.model_dump(mode="json") for j in job_scraper.scrape_jobs(req)]

    @function_tool
    def verify_company(job: dict) -> dict:
        """Check a job listing for legitimacy. Returns {verified, notes}."""
        j = Job.model_validate(job)
        legit, notes = company_verify.verify_company(j)
        return {"verified": legit and not company_verify.is_expired(j), "notes": notes}

    @function_tool
    def calculate_match_score(profile: dict, job: dict) -> dict:
        """Compute weighted compatibility score between a profile and a job."""
        return match_score.calculate_match_score(
            UserProfile.model_validate(profile), Job.model_validate(job)
        ).model_dump(mode="json")

    @function_tool
    def generate_resume(profile: dict, job: dict) -> dict:
        """Generate an ATS-safe resume tailored to a job (never invents skills)."""
        return resume_builder.generate_resume(
            UserProfile.model_validate(profile), Job.model_validate(job)
        ).model_dump(mode="json")

    @function_tool
    def generate_cover_letter(profile: dict, job: dict) -> dict:
        """Generate a tailored cover letter grounded in the CV."""
        return cover_letter.generate_cover_letter(
            UserProfile.model_validate(profile), Job.model_validate(job)
        ).model_dump(mode="json")

    @function_tool
    def analyze_skill_gap(profile: dict, job: dict) -> dict:
        """Analyze skill gaps and produce a learning roadmap."""
        return skill_gap.analyze_skill_gap(
            UserProfile.model_validate(profile), Job.model_validate(job)
        ).model_dump(mode="json")

    # --- specialist agents --------------------------------------------------
    verification_agent = Agent(
        name="JobVerificationAgent",
        instructions=("Filter job listings: remove duplicates, remove expired postings, "
                      "verify company legitimacy, flag suspicious listings."),
        model=settings.specialist_model,
        tools=[verify_company],
    )
    matching_agent = Agent(
        name="JobMatchingAgent",
        instructions=("Calculate compatibility scores between the user profile and verified "
                      "jobs. Rank by weighted skills, experience, location, goals."),
        model=settings.specialist_model,
        tools=[calculate_match_score],
    )
    resume_agent = Agent(
        name="ResumeOptimizationAgent",
        instructions=("Reorganize and highlight CV content to match the job. NEVER invent "
                      "skills or experience. Ensure ATS compatibility."),
        model=settings.specialist_model,
        tools=[generate_resume, generate_cover_letter],
    )
    skill_agent = Agent(
        name="SkillGapInterviewAgent",
        instructions="Identify skill gaps and propose a learning roadmap and interview prep.",
        model=settings.orchestrator_model,
        tools=[analyze_skill_gap],
    )

    orchestrator = Agent(
        name="CareerOrchestrator",
        instructions=(
            "Sequence the career pipeline: scrape jobs, verify, match, customize documents, "
            "and analyze skill gaps. Maintain user profile context across all handoffs."
        ),
        model=settings.orchestrator_model,
        tools=[scrape_jobs],
        handoffs=[verification_agent, matching_agent, resume_agent, skill_agent],
    )
    return orchestrator


async def run_with_sdk(user_id: str, action: str, context: Optional[dict] = None) -> str:
    """Run a free-form instruction through the SDK orchestrator."""
    from agents import Runner

    orchestrator = build_orchestrator()
    result = await Runner.run(orchestrator, input=action, context=context or {"user_id": user_id})
    return result.final_output
