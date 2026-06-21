"""CV parsing tool.

Extracts a UserProfile from raw CV text (and .docx/.pdf bytes/files if the optional
libs are present).

Extraction strategy (robust across ALL professions, not just tech):
  1. LLM extraction (preferred) - when an LLM is configured, the model reads the CV
     and returns structured fields (name, headline, summary, skills, years, titles,
     preferred locations). This works for mechanical, healthcare, finance, trades, etc.
  2. Deterministic regex fallback - used when no LLM key is set, the call fails, or
     the response can't be parsed. Keeps the system fully functional offline.

PII is scrubbed by the guardrail layer *before* this runs, so the text handed to the
LLM is already redacted.
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any, List, Optional

from ..logging_config import get_logger
from ..models.profile import UserProfile

log = get_logger("cv_parser")

_SKILL_VOCAB = {
    "python", "java", "javascript", "typescript", "react", "vue", "angular",
    "django", "fastapi", "flask", "node", "express", "aws", "gcp", "azure",
    "docker", "kubernetes", "terraform", "ansible", "postgresql", "mysql",
    "mongodb", "redis", "elasticsearch", "kafka", "spark", "pytorch",
    "tensorflow", "scikit-learn", "pandas", "numpy", "mlops", "graphql",
    "rest", "grpc", "go", "rust", "c++", "c#", "ruby", "php", "sql", "nosql",
    "ci/cd", "git", "linux", "bash",
}

# Max characters of CV text sent to the model (keeps token usage/cost bounded).
_LLM_CV_CHAR_LIMIT = 12000

_EXTRACT_SYSTEM = (
    "You are a precise, multi-domain CV parser. You extract structured facts from a CV "
    "for ANY profession (software, mechanical, healthcare, finance, skilled trades, "
    "administration, etc.). Use ONLY information present in the text; never invent "
    "skills, titles, or experience. Respond with a single JSON object and nothing else."
)

_EXTRACT_USER_TEMPLATE = (
    "Read the CV between the markers and return a STRICT JSON object with exactly these keys:\n"
    "- full_name: the candidate's name as a string, or an empty string if not present\n"
    "- headline: a short professional headline (e.g. job role + focus), or empty string\n"
    "- summary: REQUIRED, never empty. A polished 3-5 sentence professional summary in third "
    "person, grounded strictly in the CV, covering: seniority/current role, total years of "
    "experience, the strongest skills/tools, industries or domains worked in, and 1-2 notable "
    "achievements or responsibilities. Write it so it can be shown to the candidate as-is.\n"
    "- skills: array of concrete skills, tools, certifications, or competencies as lowercase "
    "strings, deduplicated; use an empty array if none are stated\n"
    "- years_experience: total years of professional experience as a number; 0 if unknown\n"
    "- titles: array of job titles the person has held or is targeting; empty array if none\n"
    "- locations_preferred: array of preferred work locations mentioned; empty array if none\n\n"
    "Rules: output ONLY the JSON object, no markdown code fences, no commentary. "
    "Keep skills generic and reusable (e.g. 'welding', 'autocad', 'patient care', "
    "'financial modeling'), not full sentences.\n\n"
    "CV TEXT (between markers):\n<<<CV\n{cv}\nCV>>>"
)


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    """Extract text from uploaded CV bytes (.pdf/.docx/.txt/.md). Plain-text fallback."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                return text
        except Exception:
            pass
    if name.endswith(".docx"):
        try:
            from docx import Document

            doc = Document(io.BytesIO(data))
            return "\n".join(par.text for par in doc.paragraphs)
        except Exception:
            pass
    return data.decode("utf-8", errors="ignore")


def read_cv_file(path: str) -> str:
    """Read CV text from a file on disk (.txt/.md/.docx/.pdf)."""
    p = Path(path)
    data = p.read_bytes()
    return extract_text_from_bytes(p.name, data)


# --------------------------------------------------------------------------- #
# Deterministic (regex) extractors - used as the offline fallback.
# --------------------------------------------------------------------------- #
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
        "architect", "designer", "lead", "consultant", "supervisor",
        "technician", "nurse", "accountant", "administrator", "officer",
        "specialist", "coordinator", "foreman", "operator", "electrician",
    ]
    titles = []
    for line in text.splitlines():
        low = line.lower().strip()
        if 0 < len(low) <= 60 and any(w in low for w in title_words):
            titles.append(line.strip())
    seen, out = set(), []
    for t in titles:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out[:5]


def _extract_name(cv_text: str) -> str:
    first_line = cv_text.strip().splitlines()[0] if cv_text.strip() else ""
    name_match = re.search(
        r"^\s*([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,3})\s*$", first_line
    )
    return name_match.group(1) if name_match else ""


# --------------------------------------------------------------------------- #
# LLM extraction + JSON coercion helpers.
# --------------------------------------------------------------------------- #
def _as_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        s = item.strip() if isinstance(item, str) else (str(item).strip() if item is not None else "")
        if s:
            out.append(s)
    return out


def _as_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r"\d+(?:\.\d+)?", value)
        if m:
            return float(m.group(0))
    return default


def _parse_json_object(raw: str) -> Optional[dict]:
    """Best-effort: pull a JSON object out of a model response."""
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        obj = json.loads(s[start : end + 1])
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _llm_extract(cv_text: str, llm: Optional[Any] = None) -> Optional[dict]:
    """Ask the configured LLM to extract structured CV fields. None on any failure."""
    text = (cv_text or "").strip()
    if not text:
        return None
    try:
        from ..agents.base import LLMClient  # lazy import avoids any circular import
    except Exception:
        return None
    client = llm or LLMClient()
    if not getattr(client, "enabled", False):
        return None
    try:
        raw = client.complete(
            model=client.settings.specialist_model,
            system=_EXTRACT_SYSTEM,
            user=_EXTRACT_USER_TEMPLATE.format(cv=text[:_LLM_CV_CHAR_LIMIT]),
        )
    except Exception as exc:  # pragma: no cover - network dependent
        log.warning("LLM CV extraction failed (%s); using regex fallback.", exc)
        return None
    data = _parse_json_object(raw or "")
    if data is None:
        log.warning("LLM CV extraction returned unparseable output; using regex fallback.")
    return data


def _fallback_summary(
    full_name: str,
    headline: str,
    titles: List[str],
    years: float,
    skills: List[str],
) -> str:
    """Build a readable summary from extracted fields when the LLM gives none."""
    who = (full_name or "").strip() or "This candidate"
    role = headline or (titles[0] if titles else "professional")
    lead = f"{who} - {headline}" if headline else f"{who} is a {role.lower()}"
    if years:
        lead += f" with {years:g}+ years of experience"
    parts: List[str] = [lead.rstrip(".") + "."]
    if titles:
        parts.append("Roles held: " + ", ".join(titles[:4]) + ".")
    if skills:
        parts.append("Core skills: " + ", ".join(skills[:10]) + ".")
    return " ".join(parts)


def parse_cv(
    user_id: str,
    cv_text: str,
    career_goals: str = "",
    llm: Optional[Any] = None,
) -> UserProfile:
    """Build a UserProfile from CV text.

    Tries the LLM first for robust, profession-agnostic extraction, then falls back
    to deterministic regex extraction for any field the LLM did not provide.
    """
    # Deterministic baseline (always computed so we have a safe fallback per field).
    full_name = _extract_name(cv_text)
    skills = _extract_skills(cv_text)
    years = _extract_years(cv_text)
    titles = _extract_titles(cv_text)
    headline = ""
    summary = ""
    locations: List[str] = []

    data = _llm_extract(cv_text, llm=llm)
    used_llm = bool(data)
    if data:
        full_name = _as_str(data.get("full_name")) or full_name
        headline = _as_str(data.get("headline")) or headline
        summary = _as_str(data.get("summary")) or summary
        llm_skills = _as_str_list(data.get("skills"))
        if llm_skills:
            skills = llm_skills
        llm_titles = _as_str_list(data.get("titles"))
        if llm_titles:
            titles = llm_titles
        years = _as_float(data.get("years_experience"), years)
        locations = _as_str_list(data.get("locations_preferred"))
        log.info(
            "LLM CV extraction: %d skill(s), %d title(s), %.1f year(s).",
            len(skills), len(titles), years,
        )

    # The CV box in the UI is filled from `summary`, so it must never be blank.
    # If the LLM gave no summary (or ran in offline/regex mode), synthesize one
    # from the extracted fields.
    if not summary:
        summary = _fallback_summary(full_name, headline, titles, years, skills)
        if used_llm:
            log.info("LLM returned no summary; used synthesized fallback summary.")

    return UserProfile(
        user_id=user_id,
        full_name=full_name,
        headline=headline,
        summary=summary,
        skills=skills,
        years_experience=years,
        titles=titles,
        locations_preferred=locations,
        career_goals=career_goals,
        raw_cv_text=cv_text,
    )
