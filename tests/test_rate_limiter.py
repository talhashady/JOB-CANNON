from career_assistant.guardrails.rate_limiter import RateLimiter
from career_assistant.models.application import Application, ApplicationStatus
from career_assistant.storage.repositories import ApplicationRepository


def _make_app(i: int) -> Application:
    return Application(
        id=f"app-{i}",
        user_id="user-1",
        job_id=f"job-{i}",
        platform="indeed",
        status=ApplicationStatus.DRY_RUN,
    )


def test_rate_limiter_blocks_after_cap():
    repo = ApplicationRepository()
    limiter = RateLimiter(repo=repo, daily_cap=3)
    for i in range(3):
        repo.save(_make_app(i))
    result = limiter.check("indeed")
    assert result.passed is False


def test_rate_limiter_allows_under_cap():
    repo = ApplicationRepository()
    limiter = RateLimiter(repo=repo, daily_cap=5)
    repo.save(_make_app(0))
    assert limiter.check("indeed").passed is True
