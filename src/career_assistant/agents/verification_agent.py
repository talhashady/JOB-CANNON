"""Verification Agent: dedupe, drop expired, verify company legitimacy."""
from __future__ import annotations

from typing import List

from .base import BaseAgent
from ..models.job import Job
from ..storage.repositories import JobRepository
from ..tools import company_verify


class VerificationAgent(BaseAgent):
    name = "JobVerificationAgent"
    instructions = (
        "Filter listings: remove duplicates and expired postings, verify company "
        "legitimacy, flag suspicious listings. Set verified per job."
    )

    def __init__(self, *args, repo: JobRepository | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.repo = repo or JobRepository()

    def run(self, jobs: List[Job]) -> List[Job]:
        seen: set[str] = set()
        verified: List[Job] = []
        for job in jobs:
            if job.dedupe_key in seen:
                continue
            seen.add(job.dedupe_key)

            notes: List[str] = []
            if company_verify.is_expired(job):
                notes.append("Listing appears expired.")
                job.verified = False
                job.verification_notes = notes
                self.repo.upsert(job)
                continue

            legit, vnotes = company_verify.verify_company(job)
            job.verified = legit
            job.verification_notes = vnotes
            self.repo.upsert(job)
            if legit:
                verified.append(job)
        self.log.info("Verified %d/%d unique jobs.", len(verified), len(jobs))
        return verified
