"""Scraping-specific exceptions."""
from __future__ import annotations


class ScrapeError(Exception):
    """Raised when a job scrape fails and DEMO_MODE is off.

    Attributes:
        original: The original exception that caused the scrape failure, if any.
    """

    def __init__(self, message: str, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original
