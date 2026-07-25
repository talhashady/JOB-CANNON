"""Company legitimacy + listing verification heuristics.

No external calls by default - uses transparent heuristics. A production version could
add a domain/registry lookup behind the same signature.
"""
from __future__ import annotations

import re
from typing import List, Tuple
from urllib.parse import urlparse

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

# Domains that are known placeholders / non-legitimate sources
_BLOCKED_DOMAINS = {
    "example.com", "example.org", "example.net",
    "localhost", "127.0.0.1", "0.0.0.0",
    "test.com", "test.org",
}


def _is_ip_address(host: str) -> bool:
    """Check if the host is a bare IP address (not a domain)."""
    import ipaddress
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def verify_company(job: Job) -> Tuple[bool, List[str]]:
    """Return (is_legit, notes). Conservative: flags obvious scam/low-quality signals."""
    notes: List[str] = []
    legit = True

    if not job.company.strip():
        notes.append("Missing company name.")
        legit = False

    # --- URL checks ---
    url = (job.url or "").strip()
    if not url:
        notes.append("Missing application URL.")
    else:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()

        # Block placeholder/test domains
        if host in _BLOCKED_DOMAINS:
            notes.append(f"URL domain '{host}' is a placeholder or test domain.")
            legit = False

        # Block bare IP addresses in job URLs
        if host and _is_ip_address(host):
            notes.append(f"URL uses an IP address ({host}) instead of a domain name.")
            legit = False

        # Warn on non-HTTPS
        if parsed.scheme and parsed.scheme != "https":
            notes.append(f"Job URL uses '{parsed.scheme}' instead of 'https'.")

    # --- Source check ---
    if job.source == "sample":
        notes.append("Synthetic sample listing (not from a real job board).")

    # --- Scam text patterns ---
    if _SCAM_RE.search(job.description or ""):
        notes.append("Description contains scam-like language.")
        legit = False

    # --- Salary plausibility ---
    if job.salary_min and job.salary_max and job.salary_max > job.salary_min * 6:
        notes.append("Implausible salary range.")
        legit = False

    # --- Description quality ---
    if len((job.description or "").strip()) < 30:
        notes.append("Suspiciously thin description.")

    return legit, notes


def is_expired(job: Job, max_age_days: int = 60) -> bool:
    """Best-effort expiry check using date_posted (YYYY-MM-DD)."""
    if not job.date_posted:
        return False
    from datetime import datetime, timezone

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            posted = datetime.strptime(job.date_posted[: len(fmt) + 2], fmt).replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - posted).days > max_age_days
        except ValueError:
            continue
    return False
