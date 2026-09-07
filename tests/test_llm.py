"""
Tests for LLM integration with Google GenAI SDK.
"""

from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from fantasy_football_ai.errors import (
    AuthenticationError,
    DataValidationError,
    RateLimitError,
)
from fantasy_football_ai.fantasy_football_ai import (
    ask_google_gemini,
    configure_llm_api,
)
from fantasy_football_ai.llm import (
    ask_llm as module_ask_llm,
)
from fantasy_football_ai.llm import (
    configure_llm_api as module_configure_llm_api,
)


class TestFantasyFootballAIGenAI:
    def test_configure_google_api_success(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-123")
        with patch("fantasy_football_ai.fantasy_football_ai.genai.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value = mock_instance

            client = configure_llm_api("google")
            mock_client_cls.assert_called_once_with(api_key="test-key-123")
            assert client == mock_instance

    def test_configure_google_api_missing_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(AuthenticationError) as exc_info:
            configure_llm_api("google")
        assert "Google API key not found" in str(exc_info.value)

    def test_ask_google_gemini_success(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Patrick Mahomes is the top QB."
        mock_client.models.generate_content.return_value = mock_response

        answer = ask_google_gemini("Who is the top QB?", "gemini-2.5-flash", client=mock_client)
        assert answer == "Patrick Mahomes is the top QB."
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-2.5-flash",
            contents="Who is the top QB?"
        )

    def test_ask_google_gemini_empty_response(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response

        with pytest.raises(DataValidationError) as exc_info:
            ask_google_gemini("Who is the top QB?", "gemini-2.5-flash", client=mock_client)
        assert "empty response" in str(exc_info.value).lower()

    def test_ask_google_gemini_auth_error(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = genai_errors.APIError(401, "Invalid API key")

        with pytest.raises(AuthenticationError):
            ask_google_gemini("Test question", "gemini-2.5-flash", client=mock_client)

    def test_ask_google_gemini_rate_limit(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = genai_errors.APIError(429, "Resource exhausted: quota exceeded")

        with pytest.raises(RateLimitError):
            ask_google_gemini("Test question", "gemini-2.5-flash", client=mock_client)


class TestLLMModuleGenAI:
    def test_module_configure_google_api(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-456")
        with patch("fantasy_football_ai.llm.genai.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value = mock_instance

            with patch("fantasy_football_ai.llm._LLM_PROVIDER", "google"):
                module_configure_llm_api()
                mock_client_cls.assert_called_once_with(api_key="test-key-456")

    def test_module_ask_llm_google_success(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Draft Christian McCaffrey."
        mock_client.models.generate_content.return_value = mock_response

        with patch("fantasy_football_ai.llm._LLM_PROVIDER", "google"), \
             patch("fantasy_football_ai.llm._LLM_MODEL", "gemini-2.5-flash"), \
             patch("fantasy_football_ai.llm._CLIENT", mock_client):
            answer = module_ask_llm("Draft advice?")
            assert answer == "Draft Christian McCaffrey."
            mock_client.models.generate_content.assert_called_once_with(
                model="gemini-2.5-flash",
                contents="Draft advice?"
            )
