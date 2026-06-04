import asyncio
import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_client import AIClient


class TestAIClientNoKey:
    def test_summarize_without_api_key(self):
        client = AIClient.__new__(AIClient)
        client.client = None
        result = asyncio.run(client.summarize_snapshots([{"mood": 5}]))
        assert "disabled" in result.lower() or "CLAUDE_API_KEY" in result


class TestAIClientInit:
    def test_client_is_none_without_key(self):
        with patch("app.services.ai_client.settings") as mock_settings:
            mock_settings.CLAUDE_API_KEY = ""
            client = AIClient()
        assert client.client is None

    def test_client_created_with_key(self):
        with patch("app.services.ai_client.settings") as mock_settings, \
             patch("app.services.ai_client.Anthropic") as mock_anthropic_cls:
            mock_settings.CLAUDE_API_KEY = "sk-ant-fake-key"
            mock_anthropic_cls.return_value = MagicMock()
            client = AIClient()
        assert client.client is not None
