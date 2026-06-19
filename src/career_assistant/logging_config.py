"""Structured logging setup shared across the app."""
from __future__ import annotations

import logging
import sys
from typing import Optional

_CONFIGURED = False


def configure_logging(level: Optional[str] = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    from .config import get_settings

    log_level = (level or get_settings().log_level or "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level, logging.INFO))
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
