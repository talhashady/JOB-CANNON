"""Explainable, weighted job-match scoring.

Weights (sum to 1.0):
  skills 0.45, experience 0.25, location 0.15, goal alignment 0.15
"""
from __future__ import annotations

import re
from typing import List, Tuple

from ..models.application import MatchResult
from ..models.job import Job
from ..models.profile import UserProfile

W_SKILLS = 0.45
W_EXPERIENCE = 0.25
W_LOCATION = 0.15
W_GOAL = 0.15

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]*")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _experience_required(description: str) -> float:
    m = re.search(r"(\d+)\+?\s*years?", description or "", re.IGNORECASE)
    return float(m.group(1)) if m else 0.0


def _skill_overlap(profile: UserProfile, job: Job) -> Tuple[float, List[str], List[str]]:
    job_tokens = _tokens(job.title) | _tokens(job.description)
    matched = sorted(s for s in profile.skills if s.lower() in job_tokens)
    # Skills the job mentions that the profile lacks (limited to known skill-like words).
    profile_skills = profile.skills_lower
    missing = sorted(
        {
            tok
            for tok in job_tokens
            if tok in _COMMON_SKILLS and tok not in profile_skills
        }
    )
    denom = max(len(profile.skills), 1)
    score = min(len(matched) / denom, 1.0) if profile.skills else 0.0
    return score, matched, missing


_COMMON_SKILLS = {
    # ── Software / IT ─────────────────────────────────────────
    "python", "java", "javascript", "typescript", "react", "django", "fastapi",
    "flask", "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
    "postgresql", "mysql", "mongodb", "redis", "pytorch", "tensorflow",
    "mlops", "spark", "kafka", "graphql", "go", "rust", "c++", "sql",
    "node.js", "vue", "angular", "next.js", "express", "spring",
    "git", "linux", "nginx", "jenkins", "ansible", "ci/cd",
    "html", "css", "tailwind", "bootstrap", "figma", "sketch",
    "swift", "kotlin", "flutter", "dart", "unity", "unreal",
    "elasticsearch", "rabbitmq", "celery", "airflow",
    "pandas", "numpy", "scikit-learn", "keras", "opencv",
    "hadoop", "hive", "presto", "dbt", "snowflake", "databricks",
    "rest", "soap", "grpc", "microservices", "serverless",
    "oauth", "jwt", "ssl", "tls", "ldap",
    "power bi", "tableau", "looker", "qlik", "metabase",
    "jira", "confluence", "trello", "asana", "notion",
    "salesforce", "hubspot", "zendesk", "servicenow",
    "blockchain", "solidity", "web3", "ethereum",
    # ── Mechanical / Maintenance / Industrial ─────────────────
    "autocad", "solidworks", "catia", "inventor", "creo", "nx",
    "ansys", "abaqus", "nastran", "comsol",
    "matlab", "simulink", "labview",
    "p&id", "pid", "piping", "isometric",
    "rotating equipment", "pumps", "compressors", "turbines",
    "heat exchangers", "boilers", "pressure vessels",
    "hvac", "chillers", "cooling towers",
    "hydraulics", "pneumatics", "valves", "actuators",
    "gearbox", "bearings", "alignment", "balancing",
    "welding", "tig", "mig", "smaw", "fcaw", "saw",
    "fabrication", "machining", "cnc", "lathe", "milling",
    "3d printing", "additive manufacturing",
    "gd&t", "tolerancing", "metrology",
    "preventive maintenance", "predictive maintenance",
    "corrective maintenance", "condition monitoring",
    "vibration analysis", "thermography", "oil analysis",
    "ultrasonic testing", "radiographic testing",
    "rcm", "fmea", "rca", "root cause analysis", "failure analysis",
    "tpm", "total productive maintenance",
    "cmms", "maximo", "sap pm", "sap mm",
    "shutdown", "turnaround", "overhaul",
    "commissioning", "pre-commissioning", "decommissioning",
    "rigging", "lifting", "crane operation",
    "scaffolding", "insulation", "lagging",
    "ndt", "nde", "dye penetrant", "magnetic particle",
    "eddy current", "phased array",
    "api-510", "api-570", "api-653", "api-580",
    "asme", "astm", "ansi", "din", "iso",
    # ── Electrical / Instrumentation / Controls ───────────────
    "electrical", "wiring", "cable tray", "conduit",
    "switchgear", "transformers", "motors", "vfd",
    "mcc", "panel board", "circuit breaker",
    "instrumentation", "calibration", "transmitters",
    "control valves", "safety valves", "relief valves",
    "plc", "dcs", "scada", "hmi", "rtu",
    "allen-bradley", "siemens", "abb", "schneider",
    "honeywell", "yokogawa", "emerson", "foxboro",
    "modbus", "profibus", "hart", "foundation fieldbus",
    "eplan", "etap", "dialux",
    "power systems", "load flow", "short circuit",
    "protection relay", "grounding", "earthing",
    "ups", "battery systems", "solar", "wind",
    # ── Civil / Structural / Construction ─────────────────────
    "structural analysis", "structural design",
    "reinforced concrete", "pre-stressed concrete",
    "steel structures", "timber structures",
    "foundation design", "pile design", "retaining walls",
    "staad pro", "etabs", "safe", "tekla", "revit",
    "primavera", "ms project", "asta powerproject",
    "quantity surveying", "bill of quantities", "boq",
    "cost estimation", "tendering", "bidding",
    "contract management", "claims management",
    "earthworks", "excavation", "piling", "shoring",
    "concrete", "formwork", "rebar", "post-tensioning",
    "road design", "pavement design", "drainage design",
    "water treatment", "wastewater treatment",
    "gis", "arcgis", "qgis", "remote sensing",
    "surveying", "total station", "gps", "lidar",
    # ── Chemical / Process / Oil & Gas ────────────────────────
    "process simulation", "hysys", "aspen plus", "chemcad",
    "process design", "process optimization",
    "distillation", "absorption", "extraction",
    "reaction engineering", "catalysis",
    "mass transfer", "heat transfer", "fluid mechanics",
    "material balance", "energy balance",
    "hazop", "pha", "lopa", "sil", "bow tie",
    "flare system", "relief system",
    "pipeline design", "flow assurance",
    "corrosion", "cathodic protection", "coating",
    "reservoir simulation", "well testing", "well completion",
    "drilling", "mud engineering", "cementing",
    "production optimization", "artificial lift",
    "subsea", "fpso", "offshore", "onshore",
    # ── HSE / Quality / Compliance ────────────────────────────
    "hse", "ehs", "safety management", "risk assessment",
    "incident investigation", "accident investigation",
    "job safety analysis", "jsa", "permit to work", "ptw",
    "confined space", "hot work", "excavation permit",
    "fire protection", "fire fighting", "emergency response",
    "first aid", "cpr", "rescue",
    "osha", "nebosh", "iosh", "niosh",
    "iso 9001", "iso 14001", "iso 45001",
    "iso 17025", "iso 22000", "iso 27001",
    "ohsas 18001", "api", "nfpa",
    "six sigma", "lean", "lean six sigma",
    "kaizen", "5s", "kanban", "value stream mapping",
    "spc", "statistical process control",
    "inspection", "audit", "surveillance",
    "quality control", "quality assurance",
    "document control", "management of change", "moc",
    # ── Project Management ────────────────────────────────────
    "project management", "program management", "portfolio management",
    "pmp", "prince2", "agile", "scrum", "kanban",
    "waterfall", "earned value management",
    "wbs", "gantt chart", "critical path method",
    "risk management", "stakeholder management",
    "change management", "scope management",
    "procurement", "contract administration",
    "epc", "design-build",
    "fidic", "nec", "jct",
    # ── Finance / Accounting ──────────────────────────────────
    "financial analysis", "financial modeling", "forecasting",
    "budgeting", "variance analysis", "cash flow",
    "gaap", "ifrs", "tax", "audit",
    "accounts payable", "accounts receivable",
    "general ledger", "trial balance", "reconciliation",
    "quickbooks", "xero", "sage", "tally",
    "bloomberg", "reuters", "factset",
    "credit analysis", "portfolio management",
    "derivatives", "fixed income", "equities",
    # ── Marketing / Sales ─────────────────────────────────────
    "seo", "sem", "ppc", "google ads", "facebook ads",
    "google analytics", "adobe analytics",
    "content marketing", "email marketing", "social media",
    "brand management", "market research", "competitive analysis",
    "crm", "lead generation", "pipeline management",
    "b2b", "b2c", "saas", "account management",
    "negotiation", "presentation", "public speaking",
    "copywriting", "editing", "proofreading",
    "adobe photoshop", "adobe illustrator", "adobe indesign",
    "canva", "premiere pro", "after effects",
    # ── HR / Admin ────────────────────────────────────────────
    "talent acquisition", "recruitment", "onboarding",
    "performance management", "succession planning",
    "compensation", "benefits", "payroll",
    "employee relations", "labor law", "employment law",
    "training", "learning and development",
    "hris", "workday", "bamboohr", "adp",
    # ── Healthcare ────────────────────────────────────────────
    "patient care", "clinical", "diagnosis", "treatment",
    "pharmacology", "pharmacy", "medication",
    "surgery", "anesthesia", "icu", "emergency",
    "radiology", "ultrasound", "mri", "ct scan",
    "laboratory", "microbiology", "pathology", "hematology",
    "infection control", "sterilization",
    "emr", "ehr", "epic", "cerner", "meditech",
    "hipaa", "jcaho", "clia",
    # ── General / ERP / Office ────────────────────────────────
    "sap", "oracle", "erp", "mrp", "mes",
    "excel", "word", "powerpoint", "outlook",
    "sharepoint", "teams", "slack", "zoom",
    "visio", "access", "vba", "macros",
    "report writing", "documentation", "technical writing",
    "communication", "leadership", "teamwork", "mentoring",
    "problem solving", "analytical", "critical thinking",
    "time management", "multitasking", "prioritization",
}


def _location_score(profile: UserProfile, job: Job) -> float:
    if job.is_remote and profile.remote_ok:
        return 1.0
    job_loc = (job.location or "").lower()
    for pref in profile.locations_preferred:
        if pref.lower() in job_loc or job_loc in pref.lower():
            return 1.0
    if "remote" in job_loc and profile.remote_ok:
        return 1.0
    return 0.3 if job_loc else 0.5


def _experience_score(profile: UserProfile, job: Job) -> float:
    required = _experience_required(job.description)
    if required <= 0:
        return 0.7
    if profile.years_experience >= required:
        return 1.0
    return max(profile.years_experience / required, 0.0)


def _goal_score(profile: UserProfile, job: Job) -> float:
    goal_tokens = _tokens(profile.career_goals) | {t.lower() for t in profile.titles}
    if not goal_tokens:
        return 0.6
    title_tokens = _tokens(job.title)
    overlap = goal_tokens & title_tokens
    return min(0.5 + 0.5 * len(overlap), 1.0)


def calculate_match_score(profile: UserProfile, job: Job) -> MatchResult:
    skill_score, matched, missing = _skill_overlap(profile, job)
    exp_score = _experience_score(profile, job)
    loc_score = _location_score(profile, job)
    goal_score = _goal_score(profile, job)

    total = (
        W_SKILLS * skill_score
        + W_EXPERIENCE * exp_score
        + W_LOCATION * loc_score
        + W_GOAL * goal_score
    )
    rationale = (
        f"skills={skill_score:.2f}, experience={exp_score:.2f}, "
        f"location={loc_score:.2f}, goals={goal_score:.2f}"
    )
    return MatchResult(
        job_id=job.id,
        score=round(total, 4),
        skill_score=round(skill_score, 4),
        experience_score=round(exp_score, 4),
        location_score=round(loc_score, 4),
        goal_score=round(goal_score, 4),
        matched_skills=matched,
        missing_skills=missing,
        rationale=rationale,
    )
