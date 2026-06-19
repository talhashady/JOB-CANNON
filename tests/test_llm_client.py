import os
from unittest.mock import MagicMock, patch
from career_assistant.config import Settings
from career_assistant.agents.base import LLMClient


def test_llm_client_initialization_with_base_url():
    settings = Settings(
        openai_api_key="test-key",
        openai_base_url="https://custom.api.endpoint/v1"
    )
    
    with patch("openai.OpenAI") as mock_openai:
        client = LLMClient(settings)
        client._ensure_client()
        mock_openai.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom.api.endpoint/v1"
        )


def test_llm_client_initialization_without_base_url():
    settings = Settings(
        openai_api_key="test-key",
        openai_base_url=""
    )
    
    with patch("openai.OpenAI") as mock_openai:
        client = LLMClient(settings)
        client._ensure_client()
        mock_openai.assert_called_once_with(
            api_key="test-key"
        )
