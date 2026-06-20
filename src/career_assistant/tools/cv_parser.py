"""CV parsing tool.

Extracts a UserProfile from raw CV text (and .docx/.pdf if the optional libs are
present). PII is scrubbed by the guardrail layer *before* this is sent to any LLM; this
parser itself only does best-effort structured extraction with no network calls.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import List

from ..models.profile import UserProfile

_SKILL_VOCAB = {
    "python", "java", "javascript", "typescript", "react", "vue", "angular",
    "django", "fastapi", "flask", "node", "express", "aws", "gcp", "azure",
    "docker", "kubernetes", "terraform", "ansible", "postgresql", "mysql",
    "mongodb", "redis", "elasticsearch", "kafka", "spark", "pytorch",
    "tensorflow", "scikit-learn", "pandas", "numpy", "mlops", "graphql",
    "rest", "grpc", "go", "rust", "c++", "c#", "ruby", "php", "sql", "nosql",
    "ci/cd", "git", "linux", "bash",
}


def read_cv_file(path: str) -> str:
    """Read CV text from .txt/.md/.docx/.pdf. Falls back to plain read."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".docx":
        try:
            from docx import Document

            return "\n".join(par.text for par in Document(str(p)).paragraphs)
        except Exception:
            pass
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(p))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            pass
    return p.read_text(encoding="utf-8", errors="ignore")


def _extract_skills(text: str) -> List[str]:
    low = text.lower()
    found = []
    for skill in _SKILL_VOCAB:
        if re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", low):
            found.append(skill)
    return sorted(found)


def _extract_years(text: str) -> float:
    matches = re.findall(r"(\d+(?:\.\d+)?)\+?\s*years?", text, re.IGNORECASE)
    return max((float(m) for m in matches), default=0.0)


def _extract_titles(text: str) -> List[str]:
    title_words = [
        "engineer", "developer", "scientist", "manager", "analyst",
        "architect", "designer", "lead", "consultant",
    ]
    titles = []
    for line in text.splitlines():
        low = line.lower().strip()
        if 0 < len(low) <= 60 and any(w in low for w in title_words):
            titles.append(line.strip())
    # de-dupe, keep up to 5
    seen, out = set(), []
    for t in titles:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out[:5]


def parse_cv(user_id: str, cv_text: str, career_goals: str = "") -> UserProfile:
    """Build a UserProfile from CV text. Email/name left to caller/guardrail."""
    name_match = re.search(r"^\s*([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,3})\s*$",
                           cv_text.strip().splitlines()[0] if cv_text.strip() else "")
    full_name = name_match.group(1) if name_match else ""
    return UserProfile(
        user_id=user_id,
        full_name=full_name,
        skills=_extract_skills(cv_text),
        years_experience=_extract_years(cv_text),
        titles=_extract_titles(cv_text),
        career_goals=career_goals,
        raw_cv_text=cv_text,
    )


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    """Extract text from uploaded CV bytes (.pdf/.docx/.txt/.md)."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            pass
    if suffix == ".docx":
        try:
            from docx import Document
            return "\n".join(par.text for par in Document(io.BytesIO(data)).paragraphs)
        except Exception:
            pass
    return data.decode("utf-8", errors="ignore")

