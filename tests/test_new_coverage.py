import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import uuid

from career_assistant.config import Settings
from career_assistant.api.app import app
from career_assistant.models.application import Application, ApplicationStatus
from career_assistant.models.job import Job, JobSearchRequest
from career_assistant.models.profile import UserProfile
from career_assistant.models.user import User
from career_assistant.agents.scraping_agent import ScrapingAgent
from career_assistant.agents.verification_agent import VerificationAgent
from career_assistant.agents.matching_agent import MatchingAgent
from career_assistant.agents.resume_agent import ResumeAgent
from career_assistant.agents.cover_letter_agent import CoverLetterAgent
from career_assistant.agents.application_agent import ApplicationAgent
from career_assistant.agents.tracking_agent import TrackingAgent
from career_assistant.agents.skill_interview_agent import SkillInterviewAgent
from career_assistant.storage.user_repository import UserRepository
from career_assistant.storage.repositories import ProfileRepository, ApplicationRepository

# --- 1. Agent Core Logic & Mocked LLM Tests ---

def test_scraping_agent_mocked():
    agent = ScrapingAgent()
    req = JobSearchRequest(query="software engineer", location="Remote", sites=["indeed"], results_wanted=5)
    with patch("career_assistant.agents.scraping_agent.job_scraper.scrape_jobs") as mock_scrape:
        mock_scrape.return_value = [
            Job(id="job-1", title="Developer", company="Acme", description="Write code", job_url="http://x")
        ]
        jobs = agent.run(req)
        assert len(jobs) == 1
        assert jobs[0].id == "job-1"

def test_verification_agent_mocked():
    agent = VerificationAgent()
    job = Job(id="job-1", title="Developer", company="Acme", description="Write code", job_url="https://acme.com/job/1")
    with patch("career_assistant.agents.base.LLMClient.complete") as mock_complete:
        mock_complete.return_value = '{"legitimate": true, "reason": "Looks good"}'
        verified = agent.run([job])
        assert len(verified) == 1
        assert verified[0].verified == 1

def test_matching_agent_mocked(profile):
    agent = MatchingAgent()
    # Verification gate requires verified=1
    job = Job(id="job-1", title="Developer", company="Acme", description="Write code", job_url="http://x", verified=1)
    res = agent.run(profile, [job], top_k=1)
    assert len(res) == 1
    assert res[0][1].score > 0.0

def test_resume_agent_mocked(profile):
    agent = ResumeAgent()
    job = Job(id="job-1", title="Developer", company="Acme", description="Write code", job_url="http://x")
    res = agent.run(profile, job)
    assert profile.full_name in res.plain_text

def test_cover_letter_agent_mocked(profile):
    # Test with LLM enabled to verify LLM completion logic and safety fallback checks
    settings = Settings(openai_api_key="test-key", specialist_model="test-model")
    agent = CoverLetterAgent(settings=settings)
    job = Job(id="job-1", title="Developer", company="Acme", description="Write code", job_url="http://x")
    with patch("career_assistant.agents.base.LLMClient.complete") as mock_complete:
        mock_complete.return_value = (
            "Dear Hiring Manager,\n\n"
            "I am writing to express my interest in the Developer position at Acme. "
            "I have extensive experience working with Python, FastAPI, Docker, and AWS to build scalable systems. "
            "In my past roles, I have designed robust backends and optimized Postgres databases. "
            "I am excited about this opportunity and look forward to contributing. "
            "I believe my background makes me a strong fit for the Developer role. "
            "Please find my resume attached for your review. "
            "Thank you for your consideration.\n\n"
            "Sincerely,\n"
            "Test User"
        )
        res = agent.run(profile, job)
        assert "build scalable systems" in res.body

def test_application_agent_mocked():
    agent = ApplicationAgent()
    job = Job(id="job-1", title="Developer", company="Acme", description="Write code", job_url="http://x")
    app_record = agent.run("user-1", job, "Resume", "Cover Letter")
    assert app_record.status == ApplicationStatus.DRY_RUN

def test_tracking_agent_transitions():
    agent = TrackingAgent()
    app_obj = Application(id="app-1", user_id="user-1", job_id="job-1", status=ApplicationStatus.DRAFT)
    
    # Valid transition: draft -> submitted
    app_obj = agent.update_status(app_obj, ApplicationStatus.SUBMITTED)
    assert app_obj.status == ApplicationStatus.SUBMITTED

    # Invalid transition: closed -> interviewing
    app_obj.status = ApplicationStatus.CLOSED
    app_obj = agent.update_status(app_obj, ApplicationStatus.INTERVIEW)
    assert app_obj.status == ApplicationStatus.CLOSED

def test_skill_interview_agent_mocked(profile):
    agent = SkillInterviewAgent()
    job = Job(id="job-1", title="Developer", company="Acme", description="Write code", job_url="http://x")
    report, interview = agent.run(profile, job)
    assert report.job_id == "job-1"
    assert len(interview.behavioral_questions) > 0

# --- 2. API Signup/Login, Cookies, Rate Limiting & Async Run Tests ---

def test_signup_login_cookie_and_rate_limiter():
    client = TestClient(app)
    
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"
    signup_payload = {"email": email, "password": "securepassword", "full_name": "New User"}
    
    res = client.post("/auth/signup", json=signup_payload, headers={"X-Requested-With": "XMLHttpRequest"})
    assert res.status_code == 200
    assert "careeros_token" in res.cookies
    assert res.json()["user"]["email"] == email

    login_payload = {"email": email, "password": "securepassword"}
    res = client.post("/auth/login", json=login_payload, headers={"X-Requested-With": "XMLHttpRequest"})
    assert res.status_code == 200
    assert "careeros_token" in res.cookies

    # Rate Limiter Trigger: make 5 more calls (total 7 from same IP + email)
    for _ in range(5):
         res = client.post("/auth/login", json=login_payload, headers={"X-Requested-With": "XMLHttpRequest"})
    
    # Should eventually hit the rate limit (5 attempts max per window)
    assert res.status_code == 429
    assert "attempts" in res.json()["detail"].lower()

def test_async_run_polling_flow(profile):
    client = TestClient(app)
    
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"
    signup_payload = {"email": email, "password": "securepassword", "full_name": "New User"}
    reg_res = client.post("/auth/signup", json=signup_payload, headers={"X-Requested-With": "XMLHttpRequest"})
    cookie = reg_res.cookies["careeros_token"]
    user_id = reg_res.json()["user"]["id"]
    
    profile.user_id = user_id
    ProfileRepository().save(profile)

    run_payload = {
        "query": "python dev",
        "location": "Remote",
        "sites": ["indeed"],
        "results_wanted": 5,
        "is_remote": True,
        "work_arrangement": "remote",
        "top_k": 1,
        "auto_apply": False
    }

    client.cookies.set("careeros_token", cookie)
    res = client.post("/run", json=run_payload, headers={"X-Requested-With": "XMLHttpRequest"})
    assert res.status_code == 202
    task_id = res.json()["task_id"]
    assert task_id

    res = client.get(f"/run/{task_id}")
    assert res.status_code == 200
    assert res.json()["status"] in ["pending", "running", "done", "error"]
