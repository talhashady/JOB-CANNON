"""FastAPI gateway exposing the career pipeline (auth-protected)."""
from __future__ import annotations

import os
import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..auth import create_access_token, hash_password, verify_password
from ..auth.dependencies import get_current_user
from ..config import get_settings
from ..logging_config import configure_logging, get_logger
from ..models.job import JobSearchRequest
from ..models.user import AuthResponse, LoginRequest, PublicUser, SignupRequest, User
from ..pipeline import CareerPipeline
from ..storage.repositories import ApplicationRepository, ProfileRepository
from ..storage.user_repository import UserRepository
from ..tools import cv_parser
from ..tools.email_apply import smtp_configured

configure_logging()
log = get_logger("api")

app = FastAPI(
    title="AI Career Assistant",
    version="0.2.0",
    description="Multi-agent job discovery, matching, customization, auto-apply, and interview prep.",
)

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

class ProfileTextRequest(BaseModel):
    cv_text: str = Field(..., min_length=1)
    career_goals: str = ""


class RunRequest(BaseModel):
    query: str = Field(..., min_length=1)
    location: str = "Remote"
    sites: List[str] = Field(default_factory=lambda: get_settings().default_job_sites)
    results_wanted: int = Field(default=25, ge=1, le=1000)
    is_remote: bool = False
    top_k: int = Field(default=5, ge=1, le=50)
    auto_apply: bool = True
    apply_min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class AutoApplyRequest(BaseModel):
    query: str = Field(..., min_length=1)
    location: str = "Remote"
    sites: List[str] = Field(default_factory=lambda: get_settings().default_job_sites)
    results_wanted: int = Field(default=50, ge=1, le=1000)
    is_remote: bool = False
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_applications: int = Field(default=10, ge=1, le=50)


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
        "smtp_configured": smtp_configured(),
        "default_sites": s.default_job_sites,
        "auto_apply_min_score": s.auto_apply_min_score,
    }


# --- auth -------------------------------------------------------------------

@app.post("/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest) -> AuthResponse:
    repo = UserRepository()
    if repo.get_by_email(req.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        full_name=req.full_name,
        password_hash=hash_password(req.password),
    )
    repo.create(user)
    token = create_access_token(user.id, {"email": str(user.email)})
    return AuthResponse(access_token=token, user=user.public())


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest) -> AuthResponse:
    user = UserRepository().get_by_email(req.email)
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token(user.id, {"email": str(user.email)})
    return AuthResponse(access_token=token, user=user.public())


@app.get("/auth/me", response_model=PublicUser)
def me(current: User = Depends(get_current_user)) -> PublicUser:
    return current.public()


# --- profiles ---------------------------------------------------------------

@app.post("/profiles")
def create_profile(req: ProfileTextRequest, current: User = Depends(get_current_user)) -> dict:
    profile = pipeline().build_profile(current.id, req.cv_text, req.career_goals)
    return profile.model_dump(mode="json")


@app.post("/profiles/upload")
async def upload_cv(
    file: UploadFile = File(...),
    career_goals: str = Form(""),
    current: User = Depends(get_current_user),
) -> dict:
    data = await file.read()
    text = cv_parser.extract_text_from_bytes(file.filename or "cv.txt", data)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from the uploaded file.")
    profile = pipeline().build_profile(current.id, text, career_goals)
    return {"profile": profile.model_dump(mode="json"), "cv_text": text}


@app.get("/profiles/me")
def get_my_profile(current: User = Depends(get_current_user)) -> dict:
    profile = ProfileRepository().get(current.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile yet. Create one first.")
    return profile.model_dump(mode="json")


# --- pipeline ---------------------------------------------------------------

@app.post("/run")
def run_pipeline(req: RunRequest, current: User = Depends(get_current_user)) -> dict:
    profile = ProfileRepository().get(current.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Create a profile first (text or upload).")
    request = JobSearchRequest(
        query=req.query, location=req.location, sites=req.sites,
        results_wanted=req.results_wanted, is_remote=req.is_remote,
    )
    return pipeline().run(
        profile, request, top_k=req.top_k,
        auto_apply=req.auto_apply, apply_min_score=req.apply_min_score,
    )


@app.post("/auto-apply")
def auto_apply(req: AutoApplyRequest, current: User = Depends(get_current_user)) -> dict:
    profile = ProfileRepository().get(current.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Create a profile first (text or upload).")
    request = JobSearchRequest(
        query=req.query, location=req.location, sites=req.sites,
        results_wanted=req.results_wanted, is_remote=req.is_remote,
    )
    return pipeline().auto_apply(
        profile, request, min_score=req.min_score, max_applications=req.max_applications,
    )


@app.get("/applications/me")
def list_my_applications(current: User = Depends(get_current_user)) -> List[dict]:
    return [a.model_dump(mode="json") for a in ApplicationRepository().list_for_user(current.id)]
