"""FastAPI gateway exposing the career pipeline.

This is the API contract the React/Next.js portal consumes (auth, CV upload, job
runner, auto-apply, application tracker). CORS is enabled so a Vercel-hosted frontend
can call a Hugging Face Spaces-hosted backend.

Auth: email/password signup + login issue a JWT (Bearer). Protected routes derive the
user from the token, so the frontend never has to pass a user_id.
"""
from __future__ import annotations

import os
import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user
from ..auth.security import create_access_token, hash_password, verify_password
from ..config import get_settings
from ..logging_config import configure_logging, get_logger
from ..models.job import JobSearchRequest
from ..models.user import AuthResponse, LoginRequest, SignupRequest, User
from ..pipeline import CareerPipeline
from ..storage.repositories import ApplicationRepository, ProfileRepository
from ..storage.user_repository import UserRepository
from ..tools import cv_parser, email_apply

configure_logging()
log = get_logger("api")

app = FastAPI(
    title="AI Career Assistant",
    version="0.2.0",
    description="Multi-agent job discovery, matching, customization, and interview prep.",
)

# --- CORS -------------------------------------------------------------------
_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def signup(req: SignupRequest) -> AuthResponse:
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
    return AuthResponse(access_token=token, user=user.public())


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest) -> AuthResponse:
    user = UserRepository().get_by_email(req.email)
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(subject=user.id, extra={"email": user.email})
    return AuthResponse(access_token=token, user=user.public())


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


# --- pipeline ---------------------------------------------------------------
@app.post("/run")
def run_pipeline(req: RunRequest, user: User = Depends(get_current_user)) -> dict:
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
    return pipeline().run(profile, request, top_k=req.top_k, auto_apply=req.auto_apply)


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
