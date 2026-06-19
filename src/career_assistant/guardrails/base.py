"""Shared guardrail result type."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class GuardResult:
    passed: bool
    issues: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:  # allows `if guard_result:`
        return self.passed
