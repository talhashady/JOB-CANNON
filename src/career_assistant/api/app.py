"""FastAPI gateway exposing the career pipeline.

This is the API contract the React/Next.js portal consumes (auth, CV upload, job
runner, auto-apply, application tracker). CORS is enabled so a Vercel-hosted frontend
can call a Hugging Face Spaces-hosted backend.

Auth: email/password signup + login issue a JWT (Cookie). Protected routes derive the
user from the token.
"""
from __future__ import annotations

import collections
import os
import threading
import time
import uuid
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
from ..models.user import AuthResponse, LoginRequest, SignupRequest, User
from ..models.profile import UserProfile
from ..pipeline import CareerPipeline
from ..storage.repositories import ApplicationRepository, ProfileRepository
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
        _origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

# --- Cross-origin detection (for cookie samesite policy) --------------------
_is_prod = _env == "production"
# If ALLOWED_ORIGINS contains a different domain than the backend, cookies need
# samesite="none" + secure=True to work across origins.
_cross_origin = any(
    not o.startswith("http://localhost") and not o.startswith("http://127.0.0.1")
    for o in _origins
) if _origins else False


def _cookie_kwargs() -> dict:
    """Return consistent cookie kwargs for signup/login/logout."""
    if _cross_origin or _is_prod:
        return {"httponly": True, "secure": True, "samesite": "none"}
    return {"httponly": True, "secure": False, "samesite": "lax"}


# --- CORS -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,  # Mandatory for HTTP cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global Exception Handlers ----------------------------------------------
@app.exception_handler(DatabaseUnavailable)
def database_unavailable_exception_handler(request: Request, exc: DatabaseUnavailable):
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable. Please try again in a few moments."},
    )


# --- In-Memory Auth Rate Limiter (Priority Item 11) ------------------------
class InMemoryRateLimiter:
    def __init__(self, requests_limit: int = 5, period_seconds: int = 60) -> None:
        self.requests_limit = requests_limit
        self.period_seconds = period_seconds
        self.history = collections.defaultdict(list)
        self.lock = threading.Lock()

    def check(self, ip: str) -> bool:
        now = time.time()
        with self.lock:
            self.history[ip] = [t for t in self.history[ip] if now - t < self.period_seconds]
            if len(self.history[ip]) >= self.requests_limit:
                return False
            self.history[ip].append(now)
            return True


auth_limiter = InMemoryRateLimiter(requests_limit=5, period_seconds=60)


def _check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    if not auth_limiter.check(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Please wait a minute and try again."
        )


# --- Async Run Tasks Store (Priority Item 4) --------------------------------
# In-memory status store for run tasks.
# Tradeoff: tasks will be lost if the Hugging Face Space sleeps/restarts.
_tasks: dict[str, dict[str, Any]] = {}
_tasks_lock = threading.Lock()


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
    auto_apply: bool = True


class AutoApplyRequest(BaseModel):
    query: str = Field(..., min_length=1)
    location: str = "Remote"
    sites: List[str] = Field(default_factory=lambda: get_settings().default_job_sites)
    results_wanted: int = Field(default=120, ge=1, le=1000)
    is_remote: bool = False
    work_arrangement: str = "any"  # any | remote | hybrid | onsite
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_applications: int = Field(default=50, ge=1, le=100)


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
@app.post("/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest, request: Request, response: Response) -> AuthResponse:
    _check_rate_limit(request)
    users = UserRepository()
    if users.email_exists(req.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        full_name=req.full_name,
        password_hash=hash_password(req.password),
    )
    users.create(user)
    token = create_access_token(subject=user.id, extra={"email": user.email})
    
    # Secure HTTP Cookie setup
    response.set_cookie(
        key="careeros_token",
        value=token,
        max_age=_settings.jwt_expire_hours * 3600,
        **_cookie_kwargs(),
    )
    return AuthResponse(access_token=token, user=user.public())


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest, request: Request, response: Response) -> AuthResponse:
    _check_rate_limit(request)
    user = UserRepository().get_by_email(req.email)
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(subject=user.id, extra={"email": user.email})
    
    # Secure HTTP Cookie setup
    response.set_cookie(
        key="careeros_token",
        value=token,
        max_age=_settings.jwt_expire_hours * 3600,
        **_cookie_kwargs(),
    )
    return AuthResponse(access_token=token, user=user.public())


@app.post("/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(
        key="careeros_token",
        **_cookie_kwargs(),
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
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    cv_text = cv_parser.extract_text_from_bytes(file.filename or "cv.txt", data)
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


# --- pipeline background execution helper -----------------------------------
def _execute_pipeline_task(task_id: str, profile: UserProfile, request: JobSearchRequest, top_k: int, auto_apply: bool):
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id]["status"] = "running"
    try:
        res = pipeline().run(profile, request, top_k=top_k, auto_apply=auto_apply)
        with _tasks_lock:
            if task_id in _tasks:
                _tasks[task_id]["status"] = "done"
                _tasks[task_id]["result"] = res
    except Exception as exc:
        log.exception("Pipeline execution failed for task %s", task_id)
        with _tasks_lock:
            if task_id in _tasks:
                _tasks[task_id]["status"] = "error"
                _tasks[task_id]["error"] = str(exc)


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
    with _tasks_lock:
        _tasks[task_id] = {
            "status": "pending",
            "user_id": user.id,
            "result": None,
            "error": None,
        }
        
    background_tasks.add_task(
        _execute_pipeline_task,
        task_id=task_id,
        profile=profile,
        request=request,
        top_k=req.top_k,
        auto_apply=req.auto_apply,
    )
    
    return {"task_id": task_id}


@app.get("/run/{task_id}")
def get_run_status(task_id: str, user: User = Depends(get_current_user)) -> dict:
    with _tasks_lock:
        task = _tasks.get(task_id)
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
        max_applications=req.max_applications,
    )


# --- applications (tracker) -------------------------------------------------
@app.get("/applications/me")
def list_my_applications(user: User = Depends(get_current_user)) -> List[dict]:
    return [a.model_dump(mode="json") for a in ApplicationRepository().list_for_user(user.id)]
