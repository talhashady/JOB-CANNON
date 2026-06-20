"""Email-based application tool.

Instead of automating Indeed/LinkedIn (against their ToS and very fragile), this:
  1. finds a contact email on the job posting (description text, and optionally by
     fetching the apply link / job URL and scanning the HTML), then
  2. submits the application by EMAIL via SMTP, attaching the tailored resume and
     cover letter.

SAFETY: nothing is ever sent unless settings.allow_live_apply is true AND SMTP is
configured. Otherwise it returns a 'dry_run' result (still resolving the target
email so the UI can show who *would* be contacted).
"""
from __future__ import annotations

import os
import re
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage
from typing import List, Optional, Tuple

from ..config import get_settings
from ..logging_config import get_logger
from ..models.job import Job

log = get_logger(__name__)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Generic / provider / system addresses we never want to apply to.
_BLOCKLIST = (
    "noreply", "no-reply", "donotreply", "do-not-reply", "mailer-daemon",
    "postmaster@", "abuse@", "privacy@", "legal@", "unsubscribe",
    "example.com", "example.org", "sentry.", "wixpress.com", "@indeed.",
    "@linkedin.", "@glassdoor.", "@ziprecruiter.", "@google.com",
)


def extract_emails(text: str) -> List[str]:
    """Return de-duplicated, plausible recipient emails from arbitrary text."""
    if not text:
        return []
    out, seen = [], set()
    for raw in _EMAIL_RE.findall(text):
        e = raw.lower().strip(".,;:()<>[]\"' ")
        if e in seen or any(b in e for b in _BLOCKLIST):
            continue
        seen.add(e)
        out.append(e)
    return out


def _fetch_url_text(url: str, timeout: float = 8.0) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (JobCannon)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(600_000).decode("utf-8", errors="ignore")
    except Exception as exc:  # network/HTTP errors are non-fatal
        log.info("Could not fetch apply link %s (%s).", url, exc)
        return ""


def _prefer_company_email(emails: List[str], company: str) -> str:
    if not company:
        return emails[0]
    token = re.sub(r"[^a-z0-9]", "", company.lower())[:5]
    for e in emails:
        domain = re.sub(r"[^a-z0-9]", "", e.split("@", 1)[1])
        if token and token[:4] and token[:4] in domain:
            return e
    return emails[0]


def find_apply_email(job: Job, fetch_remote: bool = True) -> Optional[str]:
    """Best-effort discovery of a recipient email for an application."""
    company = getattr(job, "company", "") or ""
    # 1) Inline in the description.
    candidates = extract_emails(getattr(job, "description", "") or "")
    if candidates:
        return _prefer_company_email(candidates, company)
    # 2) Fetch the apply link / job URL and scan the page.
    if fetch_remote:
        for attr in ("apply_url", "url"):
            link = getattr(job, attr, None)
            if link and isinstance(link, str) and link.startswith("http"):
                emails = extract_emails(_fetch_url_text(link))
                if emails:
                    return _prefer_company_email(emails, company)
    return None


def _smtp_config() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587") or 587),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_addr": os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")),
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").strip().lower()
        in {"1", "true", "yes", "on"},
    }


def smtp_configured() -> bool:
    c = _smtp_config()
    return bool(c["host"] and c["user"] and c["password"] and c["from_addr"])


def send_application_email(
    to_email: str,
    subject: str,
    body: str,
    resume_text: str = "",
    cover_letter_text: str = "",
) -> Tuple[str, dict]:
    """Send the application email. Returns (status, detail).

    status is one of: 'email_sent', 'dry_run', 'error'.
    """
    settings = get_settings()
    detail = {"to": to_email, "subject": subject}

    if not settings.allow_live_apply or not smtp_configured():
        detail["mode"] = "dry_run"
        detail["reason"] = (
            "ALLOW_LIVE_APPLY is false"
            if not settings.allow_live_apply
            else "SMTP not configured"
        )
        log.info("DRY RUN application email to %s (%s).", to_email, detail["reason"])
        return "dry_run", detail

    c = _smtp_config()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = c["from_addr"]
    msg["To"] = to_email
    msg["Reply-To"] = c["from_addr"]
    msg.set_content(body)
    if cover_letter_text:
        msg.add_attachment(
            cover_letter_text.encode("utf-8"), maintype="text", subtype="plain",
            filename="cover_letter.txt",
        )
    if resume_text:
        msg.add_attachment(
            resume_text.encode("utf-8"), maintype="text", subtype="plain",
            filename="resume.txt",
        )
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(c["host"], c["port"], timeout=20) as server:
            if c["use_tls"]:
                server.starttls(context=ctx)
            server.login(c["user"], c["password"])
            server.send_message(msg)
        detail["mode"] = "live"
        log.info("Application email sent to %s.", to_email)
        return "email_sent", detail
    except Exception as exc:  # never crash the pipeline on a send failure
        log.error("Email send failed: %s", exc)
        detail["error"] = str(exc)
        return "error", detail
