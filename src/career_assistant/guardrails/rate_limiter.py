"""Tool guardrail: cap applications per platform per day to avoid account flags."""
from __future__ import annotations

from typing import Optional

from .base import GuardResult
from ..config import get_settings
from ..storage.repositories import ApplicationRepository


class RateLimiter:
    def __init__(self, repo: Optional[ApplicationRepository] = None, daily_cap: Optional[int] = None) -> None:
        self.repo = repo or ApplicationRepository()
        self.daily_cap = daily_cap if daily_cap is not None else get_settings().daily_application_cap

    def check(self, platform: str) -> GuardResult:
        used = self.repo.count_submitted_today(platform)
        if used >= self.daily_cap:
            return GuardResult(
                passed=False,
                issues=[f"Daily cap reached for {platform}: {used}/{self.daily_cap}."],
            )
        return GuardResult(passed=True, issues=[f"{used}/{self.daily_cap} used today on {platform}."])
