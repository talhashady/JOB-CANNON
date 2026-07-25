"""Tool guardrail: cap applications per platform and per user per day to avoid account flags."""
from __future__ import annotations

from typing import Optional

from .base import GuardResult
from ..config import get_settings
from ..storage.repositories import ApplicationRepository


class RateLimiter:
    def __init__(
        self,
        repo: Optional[ApplicationRepository] = None,
        daily_cap: Optional[int] = None,
        user_daily_cap: Optional[int] = None,
    ) -> None:
        self.repo = repo or ApplicationRepository()
        self.daily_cap = daily_cap if daily_cap is not None else get_settings().daily_application_cap
        self.user_daily_cap = user_daily_cap if user_daily_cap is not None else get_settings().daily_application_cap

    def check(self, platform: str, user_id: Optional[str] = None) -> GuardResult:
        # Platform level check
        used_platform = self.repo.count_submitted_today(platform)
        if used_platform >= self.daily_cap:
            return GuardResult(
                passed=False,
                issues=[f"Daily cap reached for platform '{platform}': {used_platform}/{self.daily_cap}."],
            )

        # Per-user check if user_id is provided
        if user_id:
            used_user = self.repo.count_submitted_today_for_user(user_id, platform)
            if used_user >= self.user_daily_cap:
                return GuardResult(
                    passed=False,
                    issues=[f"Daily cap reached for user on '{platform}': {used_user}/{self.user_daily_cap}."],
                )
            return GuardResult(
                passed=True,
                issues=[
                    f"Platform {used_platform}/{self.daily_cap}, User {used_user}/{self.user_daily_cap} used today on {platform}."
                ],
            )

        return GuardResult(passed=True, issues=[f"{used_platform}/{self.daily_cap} used today on {platform}."])
