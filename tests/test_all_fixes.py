import pytest
from career_assistant.config import get_settings
from career_assistant.guardrails.rate_limiter import RateLimiter
from career_assistant.models.application import Application, ApplicationStatus
from career_assistant.models.job import Job, JobSearchRequest
from career_assistant.pipeline import CareerPipeline
from career_assistant.storage.repositories import ApplicationRepository
from career_assistant.storage.task_repository import TaskRepository
from career_assistant.tools.email_apply import _validate_url_safe
from career_assistant.tools.job_scraper import scrape_jobs
from career_assistant.tools.scrape_errors import ScrapeError


def test_task_repository_persistence():
    repo = TaskRepository()
    task_id = "test-task-123"
    repo.create(task_id=task_id, user_id="user-1")

    t = repo.get(task_id)
    assert t is not None
    assert t["status"] == "pending"

    repo.update(task_id, status="done", result={"scraped": 5})
    t_updated = repo.get(task_id)
    assert t_updated["status"] == "done"
    assert t_updated["result"] == {"scraped": 5}


def test_ssrf_url_validation():
    # Loopback IP / localhost must be blocked
    with pytest.raises(ValueError, match="private/loopback"):
        _validate_url_safe("https://127.0.0.1/admin")

    # Non-HTTPS must be blocked
    with pytest.raises(ValueError, match="Only HTTPS"):
        _validate_url_safe("http://example.com")


def test_demo_mode_gate(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    req = JobSearchRequest(query="invalid_job_query_xyz", sites=["nonexistent_site"])

    with pytest.raises(ScrapeError):
        scrape_jobs(req)


def test_rate_limiter_per_user():
    repo = ApplicationRepository()
    limiter = RateLimiter(repo=repo, daily_cap=10, user_daily_cap=2)

    app1 = Application(id="a1", user_id="user-A", job_id="j1", platform="indeed", status=ApplicationStatus.DRY_RUN)
    app2 = Application(id="a2", user_id="user-A", job_id="j2", platform="indeed", status=ApplicationStatus.DRY_RUN)
    repo.save(app1)
    repo.save(app2)

    # user-A hit cap of 2
    res_userA = limiter.check("indeed", user_id="user-A")
    assert res_userA.passed is False

    # user-B is under user cap
    res_userB = limiter.check("indeed", user_id="user-B")
    assert res_userB.passed is True


def test_tracking_agent_status_update(profile):
    pipeline = CareerPipeline()
    orch = pipeline.orchestrator
    repo = ApplicationRepository()

    app = Application(id="app-track-1", user_id="user-1", job_id="job-1", status=ApplicationStatus.SUBMITTED)
    repo.save(app)

    updated = orch.tracking.update_status(app, ApplicationStatus.INTERVIEW, note="Scheduled phone screen")
    assert updated.status == ApplicationStatus.INTERVIEW
    assert "Scheduled phone screen" in updated.notes


def test_pipeline_skill_score_threshold(profile):
    pipeline = CareerPipeline()
    req = JobSearchRequest(query="python developer", location="Remote", sites=["indeed"])
    
    # auto_apply with high min_skill_score threshold that excludes low skill match jobs
    res = pipeline.auto_apply(profile, req, min_score=0.5, min_skill_score=0.99, max_applications=5)
    assert res["min_skill_score"] == 0.99
