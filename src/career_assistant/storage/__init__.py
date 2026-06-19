"""Persistence layer (SQLite by default, pluggable)."""
from .database import Database, get_database
from .repositories import JobRepository, ApplicationRepository, ProfileRepository

__all__ = [
    "Database",
    "get_database",
    "JobRepository",
    "ApplicationRepository",
    "ProfileRepository",
]
