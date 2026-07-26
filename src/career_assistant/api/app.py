"""FastAPI gateway exposing the career pipeline.

This is the API contract the React/Next.js portal consumes (auth, CV upload, job
runner, auto-apply, application tracker). CORS is enabled so a Vercel-hosted frontend
can call a Hugging Face Spaces-hosted backend.

Auth: email/password signup + login issue a JWT (Cookie). Protected routes derive the
user from the token.
"""
from __future__ import annotations

import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user
from ..auth.security import create_access_token, hash_password, verify_password
from ..config import get_settings
from ..logging_config import configure_logging, get_logger
from ..models.job import JobSearchRequest
from ..models.application import ApplicationStatus
from ..models.user import AuthSuccessResponse, LoginRequest, SignupRequest, User
from ..models.profile import UserProfile
from ..pipeline import CareerPipeline
from ..storage.repositories import ApplicationRepository, ProfileRepository
from ..storage.task_repository import TaskRepository
from ..storage.user_repository import UserRepository
from ..storage.exceptions import DatabaseUnavailable
from ..tools import cv_parser, email_apply

configure_logging()
log = get_logger("api")

app = FastAPI(
    title="AI Career Assistant",
    version="0.2.0",
    description="Multi-agent job discovery, matching, customization, and interview prep.",
)

# --- Startup Environment Checks (Priority Items 10 & 12) --------------------
_env = os.environ.get("ENV", "development").strip().lower()
_settings = get_settings()

if _env == "production":
    if _settings.jwt_secret == "dev-insecure-secret-change-me":
        log.error("CRITICAL: JWT_SECRET must be configured in a production environment!")
        raise RuntimeError("CRITICAL: JWT_SECRET must be configured in a production environment!")
    
    _origins_raw = os.environ.get("ALLOWED_ORIGINS", "")
    _origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
    if not _origins or "*" in _origins:
        log.error("CRITICAL: ALLOWED_ORIGINS must be explicitly configured in a production environment (cannot be empty or '*'!)")
        raise RuntimeError("CRITICAL: ALLOWED_ORIGINS must be explicitly configured in a production environment (cannot be empty or '*'!)")
else:
    # Development: default to dev origins if not provided
    _origins_raw = os.environ.get("ALLOWED_ORIGINS", "")
    _origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
    if not _origins:
        _origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://job-cannon.vercel.app",
        ]

# --- Cross-origin detection (for cookie samesite policy) --------------------
_is_prod = _env == "production"

def _cookie_kwargs(request: Optional[Request] = None) -> dict:
    """Return consistent cookie kwargs for signup/login/logout.
    Cross-origin requests (e.g. Vercel -> Hugging Face) require samesite='none' and secure=True.
    Local HTTP requests use samesite='lax' and secure=False.
    """
    if request:
        origin = request.headers.get("origin", "")
        if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
            return {"httponly": True, "secure": False, "samesite": "lax"}
    return {"httponly": True, "secure": True, "samesite": "none"}


# --- CORS -------------------------------------------------------------------
@app.middleware("http")
async def custom_cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin", "")
    allowed_set = set(_origins)
    is_allowed = (
        not origin
        or origin in allowed_set
        or origin.endswith(".vercel.app")
        or origin.startswith("http://localhost")
        or origin.startswith("http://127.0.0.1")
    )

    if request.method == "OPTIONS":
        response = Response(status_code=204)
        if is_allowed and origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = request.headers.get(
                "Access-Control-Request-Headers", "Authorization, Content-Type, X-Requested-With, Accept"
            )
            response.headers["Access-Control-Max-Age"] = "86400"
            response.headers["Vary"] = "Origin"
        return response

    response = await call_next(request)
    if is_allowed and origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "X-Request-Id"
        response.headers["Vary"] = "Origin"
    return response


# --- Global Exception Handlers ----------------------------------------------
@app.exception_handler(DatabaseUnavailable)
def database_unavailable_exception_handler(request: Request, exc: DatabaseUnavailable):
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable. Please try again in a few moments."},
    )


# --- CSRF protection for cookie-authenticated writes -------------------------
_CSRF_EXEMPT = {"/auth/signup", "/auth/login", "/auth/logout"}
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def csrf_check(request: Request, call_next):
    """Require X-Requested-With header on state-changing cookie-authenticated requests.
    Browsers never send custom headers on cross-origin simple requests without a preflight,
    which CORS already gates. This stops CSRF from plain form submissions."""
    if request.method in _SAFE_METHODS or request.url.path in _CSRF_EXEMPT:
        return await call_next(request)
    if request.cookies.get("careeros_token") and not request.headers.get("X-Requested-With"):
        return JSONResponse(status_code=403, content={"detail": "Missing X-Requested-With header."})
    return await call_next(request)


# --- DB-backed Auth Rate Limiter --------------------------------------------
_AUTH_RATE_LIMIT = 5
_AUTH_RATE_WINDOW_S = 60


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP. Respects X-Forwarded-For when a trusted proxy header is configured."""
    trusted = os.environ.get("TRUSTED_PROXY_HEADERS", "").strip()
    if trusted:
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request, email: str = ""):
    """DB-backed rate limiter keyed by composite ip:email."""
    from ..storage.database import get_database
    ip = _get_client_ip(request)
    key = f"{ip}:{email.strip().lower()}" if email else ip
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - _AUTH_RATE_WINDOW_S
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    db = get_database()
    # Clean up old entries for this key
    db.execute("DELETE FROM auth_attempts WHERE key = ? AND ts < ?", (key, cutoff_iso))
    # Count recent attempts
    rows = db.query("SELECT COUNT(*) AS c FROM auth_attempts WHERE key = ? AND ts >= ?", (key, cutoff_iso))
    count = int(rows[0]["c"]) if rows else 0
    if count >= _AUTH_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Please wait a minute and try again."
        )
    # Record this attempt
    db.execute("INSERT INTO auth_attempts (key, ts) VALUES (?, ?)", (key, now.isoformat()))


# --- Upload validation constants --------------------------------------------
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


_pipeline: Optional[CareerPipeline] = None


def pipeline() -> CareerPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = CareerPipeline()
    return _pipeline


# --- request models ---------------------------------------------------------
class ProfileRequest(BaseModel):
    cv_text: str
    career_goals: str = ""


class RunRequest(BaseModel):
    query: str = Field(..., min_length=1)
    location: str = "Remote"
    sites: List[str] = Field(default_factory=lambda: get_settings().default_job_sites)
    results_wanted: int = Field(default=80, ge=1, le=1000)
    is_remote: bool = False
    work_arrangement: str = "any"  # any | remote | hybrid | onsite
    top_k: int = Field(default=5, ge=1, le=100)
    auto_apply: bool = False
    apply_min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    apply_min_skill_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confirm_live_apply: bool = False


class AutoApplyRequest(BaseModel):
    query: str = Field(..., min_length=1)
    location: str = "Remote"
    sites: List[str] = Field(default_factory=lambda: get_settings().default_job_sites)
    results_wanted: int = Field(default=120, ge=1, le=1000)
    is_remote: bool = False
    work_arrangement: str = "any"  # any | remote | hybrid | onsite
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_skill_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_applications: int = Field(default=50, ge=1, le=100)
    confirm_live_apply: bool = False


class UpdateApplicationStatusRequest(BaseModel):
    status: ApplicationStatus
    note: str = ""


# --- meta -------------------------------------------------------------------
@app.get("/")
def root() -> dict:
    return {"name": "AI Career Assistant API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "llm_enabled": s.llm_enabled,
        "live_apply": s.allow_live_apply,
        "smtp_configured": email_apply.smtp_configured(),
        "default_sites": s.default_job_sites,
    }


# --- auth -------------------------------------------------------------------
@app.post("/auth/signup", response_model=AuthSuccessResponse)
def signup(req: SignupRequest, request: Request, response: Response) -> AuthSuccessResponse:
    _check_rate_limit(request, email=req.email)
    users = UserRepository()
    if users.email_exists(req.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        full_name=req.full_name,
        password_hash=hash_password(req.password),
    )
    try:
        users.create(user)
    except (sqlite3.IntegrityError, Exception) as exc:
        # Catch unique-constraint race (concurrent signups with same email)
        exc_name = type(exc).__name__
        if "IntegrityError" in exc_name or "UniqueViolation" in exc_name:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        raise
    token = create_access_token(subject=user.id, extra={"email": user.email})
    
    # Secure HTTP Cookie setup
    response.set_cookie(
        key="careeros_token",
        value=token,
        max_age=_settings.jwt_expire_hours * 3600,
        **_cookie_kwargs(request),
    )
    return AuthSuccessResponse(user=user.public(), token=token)


@app.post("/auth/login", response_model=AuthSuccessResponse)
def login(req: LoginRequest, request: Request, response: Response) -> AuthSuccessResponse:
    _check_rate_limit(request, email=req.email)
    user = UserRepository().get_by_email(req.email)
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(subject=user.id, extra={"email": user.email})
    
    # Secure HTTP Cookie setup
    response.set_cookie(
        key="careeros_token",
        value=token,
        max_age=_settings.jwt_expire_hours * 3600,
        **_cookie_kwargs(request),
    )
    return AuthSuccessResponse(user=user.public(), token=token)


@app.post("/auth/logout")
def logout(request: Request, response: Response) -> dict:
    response.delete_cookie(
        key="careeros_token",
        **_cookie_kwargs(request),
    )
    return {"status": "logged_out"}


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return user.public().model_dump(mode="json")


# --- profile ----------------------------------------------------------------
@app.post("/profiles")
def create_profile(req: ProfileRequest, user: User = Depends(get_current_user)) -> dict:
    profile = pipeline().build_profile(user.id, req.cv_text, req.career_goals)
    return profile.model_dump(mode="json")


@app.post("/profiles/upload")
async def upload_profile(
    file: UploadFile = File(...),
    career_goals: str = Form(""),
    user: User = Depends(get_current_user),
) -> dict:
    """Drag-and-drop CV upload: parse .pdf/.docx/.txt into a profile."""
    filename = file.filename or "cv.txt"
    ext = PurePosixPath(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )
    # Stream-read with size cap
    data = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum upload size is {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        cv_text = cv_parser.extract_text_from_bytes(filename, data)
    except Exception as exc:
        log.warning("Failed to parse uploaded file '%s': %s", filename, exc)
        raise HTTPException(status_code=422, detail="Could not parse the uploaded file. Ensure it is a valid PDF, DOCX, or text file.")
    if not cv_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from the file")
    profile = pipeline().build_profile(user.id, cv_text, career_goals)
    return profile.model_dump(mode="json")


@app.get("/profiles/me")
def get_my_profile(user: User = Depends(get_current_user)) -> dict:
    profile = ProfileRepository().get(user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.model_dump(mode="json")


class PrepareRequest(BaseModel):
    job_ids: List[str] = Field(..., min_length=1, max_length=20)
    auto_apply: bool = False
    confirm_live_apply: bool = False


# --- pipeline background execution helper -----------------------------------
def _execute_pipeline_task(
    task_id: str,
    profile: UserProfile,
    request: JobSearchRequest,
    top_k: int,
    auto_apply: bool,
    apply_min_score: Optional[float] = None,
    apply_min_skill_score: Optional[float] = None,
    confirm_live_apply: bool = False,
):
    repo = TaskRepository()
    repo.update(task_id, status="running")
    try:
        res = pipeline().run(
            profile,
            request,
            top_k=top_k,
            auto_apply=auto_apply,
            apply_min_score=apply_min_score,
            apply_min_skill_score=apply_min_skill_score,
            confirm_live_apply=confirm_live_apply,
        )
        repo.update(task_id, status="done", result=res)
    except Exception as exc:
        log.exception("Pipeline execution failed for task %s", task_id)
        repo.update(task_id, status="error", error=str(exc))


def _execute_discovery_task(
    task_id: str,
    profile: UserProfile,
    request: JobSearchRequest,
    top_k: int,
):
    repo = TaskRepository()
    repo.update(task_id, status="running")
    try:
        res = pipeline().run_discovery(profile, request, top_k=top_k)
        repo.update(task_id, status="done", result=res)
    except Exception as exc:
        log.exception("Discovery execution failed for task %s", task_id)
        repo.update(task_id, status="error", error=str(exc))


def _execute_prepare_task(
    task_id: str,
    profile: UserProfile,
    job_ids: List[str],
    auto_apply: bool,
    confirm_live_apply: bool = False,
):
    repo = TaskRepository()
    repo.update(task_id, status="running")
    try:
        res = pipeline().run_prepare(
            profile,
            job_ids,
            auto_apply=auto_apply,
            confirm_live_apply=confirm_live_apply,
        )
        repo.update(task_id, status="done", result=res)
    except Exception as exc:
        log.exception("Prepare execution failed for task %s", task_id)
        repo.update(task_id, status="error", error=str(exc))


# --- pipeline routes --------------------------------------------------------
@app.post("/run", status_code=202)
def run_pipeline(
    req: RunRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> dict:
    profile = ProfileRepository().get(user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Create a profile first via POST /profiles")
    
    request = JobSearchRequest(
        query=req.query,
        location=req.location,
        sites=req.sites,
        results_wanted=req.results_wanted,
        is_remote=req.is_remote or req.work_arrangement == "remote",
        work_arrangement=req.work_arrangement,
    )
    
    task_id = str(uuid.uuid4())
    task_repo = TaskRepository()

    from ..storage.task_repository import MAX_CONCURRENT_TASKS_PER_USER
    active = task_repo.count_active_for_user(user.id)
    if active >= MAX_CONCURRENT_TASKS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"You already have {active} active pipeline tasks. Please wait for them to complete.",
        )

    task_repo.create(task_id=task_id, user_id=user.id)
    task_repo.cleanup_expired()
        
    background_tasks.add_task(
        _execute_pipeline_task,
        task_id=task_id,
        profile=profile,
        request=request,
        top_k=req.top_k,
        auto_apply=req.auto_apply,
        apply_min_score=req.apply_min_score,
        apply_min_skill_score=req.apply_min_skill_score,
        confirm_live_apply=req.confirm_live_apply,
    )
    
    return {"task_id": task_id}


@app.post("/run/discover", status_code=202)
def run_discovery_pipeline(
    req: RunRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> dict:
    """Phase 1: Scrape -> Verify -> Match. Returns ranked jobs without generating documents."""
    profile = ProfileRepository().get(user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Create a profile first via POST /profiles")
    
    request = JobSearchRequest(
        query=req.query,
        location=req.location,
        sites=req.sites,
        results_wanted=req.results_wanted,
        is_remote=req.is_remote or req.work_arrangement == "remote",
        work_arrangement=req.work_arrangement,
    )
    
    task_id = str(uuid.uuid4())
    task_repo = TaskRepository()

    from ..storage.task_repository import MAX_CONCURRENT_TASKS_PER_USER
    active = task_repo.count_active_for_user(user.id)
    if active >= MAX_CONCURRENT_TASKS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"You already have {active} active pipeline tasks. Please wait for them to complete.",
        )

    task_repo.create(task_id=task_id, user_id=user.id)
    task_repo.cleanup_expired()
        
    background_tasks.add_task(
        _execute_discovery_task,
        task_id=task_id,
        profile=profile,
        request=request,
        top_k=req.top_k,
    )
    
    return {"task_id": task_id}


@app.post("/run/prepare", status_code=202)
def run_prepare_pipeline(
    req: PrepareRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> dict:
    """Phase 2: Resume -> Cover Letter -> Apply -> Skills for user-selected jobs."""
    profile = ProfileRepository().get(user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Create a profile first via POST /profiles")
    
    task_id = str(uuid.uuid4())
    task_repo = TaskRepository()

    from ..storage.task_repository import MAX_CONCURRENT_TASKS_PER_USER
    active = task_repo.count_active_for_user(user.id)
    if active >= MAX_CONCURRENT_TASKS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"You already have {active} active pipeline tasks. Please wait for them to complete.",
        )

    task_repo.create(task_id=task_id, user_id=user.id)
    task_repo.cleanup_expired()
        
    background_tasks.add_task(
        _execute_prepare_task,
        task_id=task_id,
        profile=profile,
        job_ids=req.job_ids,
        auto_apply=req.auto_apply,
        confirm_live_apply=req.confirm_live_apply,
    )
    
    return {"task_id": task_id}


@app.get("/run/{task_id}")
def get_run_status(task_id: str, user: User = Depends(get_current_user)) -> dict:
    task_repo = TaskRepository()
    task_repo.expire_stale_running(max_age_seconds=600)
    task = task_repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    return {
        "status": task["status"],
        "result": task["result"],
        "error": task["error"]
    }


@app.post("/auto-apply")
def auto_apply(req: AutoApplyRequest, user: User = Depends(get_current_user)) -> dict:
    profile = ProfileRepository().get(user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Create a profile first via POST /profiles")
    request = JobSearchRequest(
        query=req.query,
        location=req.location,
        sites=req.sites,
        results_wanted=req.results_wanted,
        is_remote=req.is_remote or req.work_arrangement == "remote",
        work_arrangement=req.work_arrangement,
    )
    return pipeline().auto_apply(
        profile,
        request,
        min_score=req.min_score,
        min_skill_score=req.min_skill_score,
        max_applications=req.max_applications,
        confirm_live_apply=req.confirm_live_apply,
    )


# --- applications (tracker) -------------------------------------------------
@app.get("/applications/me")
def list_my_applications(user: User = Depends(get_current_user)) -> List[dict]:
    return [a.model_dump(mode="json") for a in ApplicationRepository().list_for_user(user.id)]


@app.patch("/applications/{id}/status")
def update_application_status(
    id: str,
    req: UpdateApplicationStatusRequest,
    user: User = Depends(get_current_user),
) -> dict:
    app_repo = ApplicationRepository()
    application = app_repo.get(id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this application")
    
    tracking = pipeline().orchestrator.tracking
    updated = tracking.update_status(application, req.status, note=req.note)
    return updated.model_dump(mode="json")

