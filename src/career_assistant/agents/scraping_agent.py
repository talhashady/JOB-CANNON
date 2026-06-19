"""Scraping Agent: collects jobs via JobSpy and persists them."""
from __future__ import annotations

from typing import List

from .base import BaseAgent
from ..models.job import Job, JobSearchRequest
from ..storage.repositories import JobRepository
from ..tools import job_scraper


class ScrapingAgent(BaseAgent):
    name = "JobScrapingAgent"
    instructions = (
        "Collect job listings from configured boards via JobSpy. Normalize results and "
        "honor the 1000-results-per-search cap."
    )

    def __init__(self, *args, repo: JobRepository | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.repo = repo or JobRepository()

    def run(self, request: JobSearchRequest) -> List[Job]:
        jobs = job_scraper.scrape_jobs(request)
        self.repo.upsert_many(jobs)
        self.log.info("Scraped and stored %d jobs.", len(jobs))
        return jobs
