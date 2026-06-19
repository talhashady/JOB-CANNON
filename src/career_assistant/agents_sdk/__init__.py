"""Optional OpenAI Agents SDK adapter.

This package wraps the deterministic tools in this repo as real OpenAI Agents SDK
`Agent`s + `function_tool`s, so the same pipeline can run on the official SDK when
`openai-agents` is installed and an API key is configured.

Importing this package never hard-fails: if the SDK is missing, `is_available()`
returns False and the rest of the app keeps using the built-in orchestrator.
"""
from .adapter import build_orchestrator, is_available, run_with_sdk

__all__ = ["build_orchestrator", "is_available", "run_with_sdk"]
