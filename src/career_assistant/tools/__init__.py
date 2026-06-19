"""Function tools used by agents.

Each tool is a plain, typed callable with JSON-serializable I/O so it can be wrapped
with the OpenAI Agents SDK `function_tool` without modification.
"""
from . import (
    job_scraper,
    company_verify,
    match_score,
    cv_parser,
    resume_builder,
    cover_letter,
    application_submit,
    skill_gap,
)

__all__ = [
    "job_scraper",
    "company_verify",
    "match_score",
    "cv_parser",
    "resume_builder",
    "cover_letter",
    "application_submit",
    "skill_gap",
]
