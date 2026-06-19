"""Company legitimacy + listing verification heuristics.

No external calls by default - uses transparent heuristics. A production version could
add a domain/registry lookup behind the same signature.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from ..models.job import Job

_SCAM_PATTERNS = [
    r"\bwire transfer\b",
    r"\bpay (?:a )?fee\b",
    r"\bsend (?:money|gift cards?)\b",
    r"\bregistration fee\b",
    r"\bwhatsapp only\b",
    r"\btelegram only\b",
    r"\bno experience needed.*\$\d{3,}/day\b",
]

_SCAM_RE = re.compile("|".join(_SCAM_PATTERNS), re.IGNORECASE)


def verify_company(job: Job) -> Tuple[bool, List[str]]:
    """Return (is_legit, notes). Conservative: flags obvious scam/low-quality signals."""
    notes: List[str] = []
    legit = True

    if not job.company.strip():
        notes.append("Missing company name.")
        legit = False

    if not job.url.strip():
        notes.append("Missing application URL.")

    if _SCAM_RE.search(job.description or ""):
        notes.append("Description contains scam-like language.")
        legit = False

    if job.salary_min and job.salary_max and job.salary_max > job.salary_min * 6:
        notes.append("Implausible salary range.")
        legit = False

    if len((job.description or "").strip()) < 30:
        notes.append("Suspiciously thin description.")

    return legit, notes


def is_expired(job: Job, max_age_days: int = 60) -> bool:
    """Best-effort expiry check using date_posted (YYYY-MM-DD)."""
    if not job.date_posted:
        return False
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            posted = datetime.strptime(job.date_posted[: len(fmt) + 2], fmt)
            return (datetime.utcnow() - posted).days > max_age_days
        except ValueError:
            continue
    return False
