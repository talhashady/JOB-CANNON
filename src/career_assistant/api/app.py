"""FastAPI gateway exposing the career pipeline.

This is the API contract the React/Next.js portal consumes (dashboard, CV upload,
job browser, application tracker). CORS is enabled so a Vercel-hosted frontend can
call a Hugging Face Spaces-hosted backend.
"""
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..config import get_settings
from ..logging_config import configure_logging, get_logger
from ..models.job import JobSearchRequest
from ..pipeline import CareerPipeline
from ..storage.repositories import ApplicationRepository, ProfileRepository

configure_logging()
log = get_logger("api")

app = FastAPI(
    title="AI Career Assistant",
    version="0.1.0",
    description="Multi-agent job discovery, matching, customization, and interview prep.",
)

# --- CORS -------------------------------------------------------------------
# Comma-separated allowed origins. Default "*" for easy first deploy; lock this
# down to your Vercel domain in production via the ALLOWED_ORIGINS env var.
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


class ProfileRequest(BaseModel):
    user_id: str
    cv_text: str
    career_goals: str = ""


class RunRequest(BaseModel):
    user_id: str
    query: str = Field(..., min_length=1)
    location: str = "Remote"
    sites: List[str] = Field(default_factory=lambda: get_settings().default_job_sites)
    results_wanted: int = Field(default=25, ge=1, le=1000)
    is_remote: bool = False
    top_k: int = Field(default=5, ge=1, le=50)
    auto_apply: bool = True


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
        "default_sites": s.default_job_sites,
    }


@app.post("/profiles")
def create_profile(req: ProfileRequest) -> dict:
    profile = pipeline().build_profile(req.user_id, req.cv_text, req.career_goals)
    return profile.model_dump(mode="json")


@app.get("/profiles/{user_id}")
def get_profile(user_id: str) -> dict:
    profile = ProfileRepository().get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.model_dump(mode="json")


@app.post("/run")
def run_pipeline(req: RunRequest) -> dict:
    profile = ProfileRepository().get(req.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Create a profile first via POST /profiles")
    request = JobSearchRequest(
        query=req.query,
        location=req.location,
        sites=req.sites,
        results_wanted=req.results_wanted,
        is_remote=req.is_remote,
    )
    return pipeline().run(profile, request, top_k=req.top_k, auto_apply=req.auto_apply)


@app.get("/applications/{user_id}")
def list_applications(user_id: str) -> List[dict]:
    return [a.model_dump(mode="json") for a in ApplicationRepository().list_for_user(user_id)]
