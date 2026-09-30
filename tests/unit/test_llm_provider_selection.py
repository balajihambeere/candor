"""Verifies the provider factory picks the right client and fails clearly
when a key is missing — without making a real network call to either
provider.
"""

from unittest.mock import MagicMock, patch

import pytest

from packages.candor.llm import AnthropicJustifyClient, OpenAIJustifyClient, build_llm_client


class _FakeSettings:
    def __init__(self, **overrides):
        self.llm_provider = "anthropic"
        self.anthropic_api_key = "sk-ant-test"
        self.anthropic_model = "claude-sonnet-5"
        self.anthropic_timeout_seconds = 20.0
        self.anthropic_max_retries = 2
        self.openai_api_key = None
        self.openai_model = "gpt-4o-mini"
        self.openai_timeout_seconds = 20.0
        self.openai_max_retries = 2
        for key, value in overrides.items():
            setattr(self, key, value)


def test_build_llm_client_defaults_to_anthropic():
    with patch("packages.candor.llm.get_settings", return_value=_FakeSettings()):
        client = build_llm_client()
    assert isinstance(client, AnthropicJustifyClient)


def test_build_llm_client_selects_openai():
    settings = _FakeSettings(llm_provider="openai", openai_api_key="sk-test")
    with patch("packages.candor.llm.get_settings", return_value=settings):
        client = build_llm_client()
    assert isinstance(client, OpenAIJustifyClient)


def test_build_llm_client_raises_when_anthropic_key_missing():
    settings = _FakeSettings(anthropic_api_key=None)
    with patch("packages.candor.llm.get_settings", return_value=settings):
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            build_llm_client()


def test_build_llm_client_raises_when_openai_key_missing():
    settings = _FakeSettings(llm_provider="openai", openai_api_key=None)
    with patch("packages.candor.llm.get_settings", return_value=settings):
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            build_llm_client()


def test_build_llm_client_raises_on_unknown_provider():
    settings = _FakeSettings(llm_provider="not-a-real-provider")
    with patch("packages.candor.llm.get_settings", return_value=settings):
        with pytest.raises(RuntimeError, match="Unknown LLM_PROVIDER"):
            build_llm_client()


def test_openai_client_extracts_text_from_chat_completion():
    settings = _FakeSettings(openai_api_key="sk-test")
    with patch("packages.candor.llm.get_settings", return_value=settings):
        client = OpenAIJustifyClient()

    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="Your return was not approved."))]
    client._client.chat.completions.create = MagicMock(return_value=fake_response)

    sentence = client.generate_sentence([{"description": "late", "evaluated_value": 9, "threshold": 7}])

    assert sentence == "Your return was not approved."
    call_kwargs = client._client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["messages"][0]["role"] == "system"
    assert call_kwargs["messages"][1]["role"] == "user"
