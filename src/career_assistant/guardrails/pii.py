"""Input guardrail: scrub sensitive PII from CV text before any model/tool sees it.

Strips national IDs, bank/card numbers, IBANs, and similar high-risk identifiers.
Email/phone are masked (not removed) since they are sometimes needed for applications,
but they are masked before reaching an LLM.
"""
from __future__ import annotations

import re
from typing import Tuple

# Order matters: most specific first.
_PATTERNS = [
    # Credit/debit card (13-16 digits, optional separators)
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_CARD]"),
    # IBAN
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"), "[REDACTED_IBAN]"),
    # US SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    # Generic national ID (CNIC-style 5-7-1, etc.)
    (re.compile(r"\b\d{5}-\d{7}-\d\b"), "[REDACTED_NATIONAL_ID]"),
    # Email -> masked
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    # Phone numbers (loose, international)
    (re.compile(r"(?<!\d)(?:\+?\d[\d -]{7,}\d)(?!\d)"), "[PHONE]"),
]


def scrub_pii(text: str) -> Tuple[str, int]:
    """Return (scrubbed_text, replacement_count)."""
    if not text:
        return text, 0
    count = 0
    scrubbed = text
    for pattern, replacement in _PATTERNS:
        scrubbed, n = pattern.subn(replacement, scrubbed)
        count += n
    return scrubbed, count
