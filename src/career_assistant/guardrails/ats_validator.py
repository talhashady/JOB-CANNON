"""Output guardrail: reject resume layouts that ATS parsers struggle with.

Checks for tables, multi-column markers, image/graphic markup, and excessive special
characters - all common causes of ATS parse failures.
"""
from __future__ import annotations

import re

from .base import GuardResult

_BAD_MARKERS = [
    (re.compile(r"<table|</table>|<img|<svg|\[image\]", re.IGNORECASE), "Contains tables or images."),
    (re.compile(r"\t.*\t.*\t"), "Looks multi-column (multiple tab stops per line)."),
    (re.compile(r"[\u2022\u25CF\u25AA]{2,}"), "Decorative bullet runs."),
]


def validate_ats(resume_text: str) -> GuardResult:
    issues = []
    for pattern, message in _BAD_MARKERS:
        if pattern.search(resume_text or ""):
            issues.append(message)
    # Heuristic: too many non-ascii symbols suggests graphics/odd formatting.
    non_ascii = sum(1 for ch in (resume_text or "") if ord(ch) > 127)
    if resume_text and non_ascii / max(len(resume_text), 1) > 0.05:
        issues.append("High ratio of non-ASCII characters.")
    return GuardResult(passed=len(issues) == 0, issues=issues)
