"""Application submission tool.

SAFETY: by default this performs a DRY RUN - it records intent but never submits to a
real site. Live submission requires settings.allow_live_apply AND a registered backend
via `register_submission_backend`. This prevents ToS violations and account flags.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

from ..config import get_settings
from ..logging_config import get_logger
from ..models.job import Job

log = get_logger(__name__)

# A live backend must accept (job, resume_text, cover_letter_text) and return a confirmation
# string. None means "no live backend registered" -> dry run only.
SubmissionBackend = Callable[[Job, str, str], str]
_BACKEND: Optional[SubmissionBackend] = None


def register_submission_backend(backend: SubmissionBackend) -> None:
    """Opt-in hook for a real submission integration (e.g. Selenium driver)."""
    global _BACKEND
    _BACKEND = backend
    log.warning("Live submission backend registered. Real applications may be submitted.")


def submit_application(
    job: Job,
    resume_text: str,
    cover_letter_text: str,
) -> Tuple[str, Dict[str, str]]:
    """Return (status, detail). status is 'dry_run' or 'submitted'."""
    settings = get_settings()
    detail = {"job_id": job.id, "company": job.company, "url": job.url}

    if not settings.allow_live_apply or _BACKEND is None:
        log.info("DRY RUN: prepared application for '%s' at %s (not submitted).",
                 job.title, job.company)
        detail["mode"] = "dry_run"
        return "dry_run", detail

    try:
        confirmation = _BACKEND(job, resume_text, cover_letter_text)
        detail["confirmation"] = confirmation
        detail["mode"] = "live"
        log.info("Submitted application for '%s' at %s.", job.title, job.company)
        return "submitted", detail
    except Exception as exc:  # never let a submission failure crash the pipeline
        log.error("Live submission failed: %s", exc)
        detail["error"] = str(exc)
        return "error", detail
