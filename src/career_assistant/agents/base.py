"""Agent base class + optional LLM client.

Mirrors the OpenAI Agents SDK Agent contract (name, instructions, model, tools) while
adding a deterministic fallback so the whole system runs offline. Subclasses implement
`run(...)`; they may call `self.llm.complete(...)` which no-ops to None when no key is set.
"""
from __future__ import annotations

from typing import Any, List, Optional

from ..config import Settings, get_settings
from ..logging_config import get_logger


class LLMClient:
    """Tiny wrapper over the OpenAI client. Returns None when disabled/unavailable."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client = None
        self.log = get_logger("llm")

    @property
    def enabled(self) -> bool:
        return self.settings.llm_enabled

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.enabled:
            return None
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.settings.openai_api_key)
        except Exception as exc:  # pragma: no cover - depends on optional dep
            self.log.warning("OpenAI client unavailable (%s); using fallbacks.", exc)
            self._client = None
        return self._client

    def complete(self, *, model: str, system: str, user: str) -> Optional[str]:
        """Return model text, or None to signal the caller to use its fallback."""
        client = self._ensure_client()
        if client is None:
            return None
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except Exception as exc:  # pragma: no cover - network dependent
            self.log.warning("LLM call failed (%s); using fallback.", exc)
            return None


class BaseAgent:
    name: str = "BaseAgent"
    instructions: str = ""

    def __init__(self, llm: Optional[LLMClient] = None, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.llm = llm or LLMClient(self.settings)
        self.log = get_logger(f"agent.{self.name}")

    @property
    def model(self) -> str:
        return self.settings.specialist_model

    def run(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - abstract
        raise NotImplementedError
