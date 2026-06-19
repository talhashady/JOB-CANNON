"""Matching Agent: ranks ONLY verified jobs by weighted compatibility."""
from __future__ import annotations

from typing import List, Tuple

from .base import BaseAgent
from ..models.application import MatchResult
from ..models.job import Job
from ..models.profile import UserProfile
from ..tools import match_score


class MatchingAgent(BaseAgent):
    name = "JobMatchingAgent"
    instructions = (
        "Calculate compatibility scores between the user profile and verified jobs. "
        "Rank by weighted skills, experience, location, and goal alignment. "
        "Only rank jobs with verified == True (verification gate)."
    )

    def run(self, profile: UserProfile, jobs: List[Job], top_k: int = 10) -> List[Tuple[Job, MatchResult]]:
        # Verification gate: never rank unverified listings.
        eligible = [j for j in jobs if j.verified]
        scored = [(job, match_score.calculate_match_score(profile, job)) for job in eligible]
        scored.sort(key=lambda pair: pair[1].score, reverse=True)
        self.log.info("Ranked %d verified jobs; returning top %d.", len(scored), min(top_k, len(scored)))
        return scored[:top_k]
