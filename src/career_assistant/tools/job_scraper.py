"""Job discovery tool backed by JobSpy.

JobSpy (https://github.com/speedyapply/JobSpy) aggregates Indeed, LinkedIn, Glassdoor,
Google and ZipRecruiter. Indeed is its strongest board (no rate limiting) and all boards
are capped at ~1000 results per search - we honor that cap.

If JobSpy is not installed or the network is unavailable, this tool transparently returns
realistic sample jobs so the rest of the pipeline can run end-to-end.
"""
from __future__ import annotations

from typing import List

from ..logging_config import get_logger
from ..models.job import Job, JobSearchRequest

log = get_logger(__name__)


def _to_float(value) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        return f if f == f else None  # filter NaN
    except (TypeError, ValueError):
        return None


def scrape_jobs(request: JobSearchRequest) -> List[Job]:
    """Scrape jobs for a request. Returns normalized Job models."""
    try:
        return _scrape_with_jobspy(request)
    except ImportError:
        log.warning("python-jobspy not installed; returning sample jobs. "
                    "Install with `pip install python-jobspy` for live data.")
    except Exception as exc:  # network / board errors -> degrade gracefully
        log.warning("JobSpy scrape failed (%s); returning sample jobs.", exc)
    return _sample_jobs(request)


def _scrape_with_jobspy(request: JobSearchRequest) -> List[Job]:
    from jobspy import scrape_jobs as jobspy_scrape  # type: ignore

    df = jobspy_scrape(
        site_name=request.sites,
        search_term=request.query,
        location=request.location,
        results_wanted=min(request.results_wanted, 1000),
        hours_old=request.hours_old,
        is_remote=request.is_remote,
        country_indeed=request.country,
    )
    jobs: List[Job] = []
    if df is None or len(df) == 0:
        return jobs
    for _, row in df.iterrows():
        jobs.append(
            Job(
                source=str(row.get("site", "unknown")),
                title=str(row.get("title", "")).strip(),
                company=str(row.get("company", "") or "").strip(),
                location=str(row.get("location", "") or "").strip(),
                description=str(row.get("description", "") or ""),
                url=str(row.get("job_url", "") or ""),
                salary_min=_to_float(row.get("min_amount")),
                salary_max=_to_float(row.get("max_amount")),
                currency=str(row.get("currency")) if row.get("currency") else None,
                is_remote=bool(row.get("is_remote", False)),
                date_posted=str(row.get("date_posted")) if row.get("date_posted") else None,
            )
        )
    log.info("JobSpy returned %d jobs for '%s'", len(jobs), request.query)
    return jobs


def _sample_jobs(request: JobSearchRequest) -> List[Job]:
    """Deterministic sample data mirroring JobSpy's shape (offline/dev mode)."""
    base = [
        ("Senior Python Developer", "Acme Cloud", 120000, 160000, ["python", "fastapi", "aws", "postgresql"]),
        ("Backend Engineer (Python)", "DataForge", 110000, 145000, ["python", "django", "docker", "redis"]),
        ("Machine Learning Engineer", "NeuraLabs", 130000, 175000, ["python", "pytorch", "mlops", "aws"]),
        ("Full Stack Developer", "BrightApps", 95000, 130000, ["python", "react", "typescript", "docker"]),
        ("Platform Engineer", "ScaleOps", 125000, 165000, ["python", "kubernetes", "terraform", "aws"]),
    ]
    jobs: List[Job] = []
    n = min(request.results_wanted, len(base))
    for i in range(n):
        title, company, lo, hi, skills = base[i]
        jobs.append(
            Job(
                source=request.sites[0] if request.sites else "sample",
                title=title,
                company=company,
                location=request.location,
                description=(
                    f"We are hiring a {title} at {company}. "
                    f"Required skills: {', '.join(skills)}. "
                    f"3+ years experience. {'Remote friendly.' if request.is_remote else ''}"
                ),
                url="https://example.com/jobs/" + company.lower().replace(" ", "-") + f"-{i}",
                salary_min=float(lo),
                salary_max=float(hi),
                currency="$",
                is_remote=request.is_remote or "remote" in request.location.lower(),
                date_posted="2026-06-18",
            )
        )
    log.info("Generated %d sample jobs (offline mode).", len(jobs))
    return jobs
