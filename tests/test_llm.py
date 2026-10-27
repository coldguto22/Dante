from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from dante.config import Settings
from dante.llm import OllamaLLM
from dante.models import ActivityProposal


class FakeOllamaClient:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content=self.content))


def test_chat_passes_configured_temperature_and_seed():
    client = FakeOllamaClient("hello")
    llm = OllamaLLM(Settings(temperature=0.25, seed=123), client=client)

    assert llm.chat([{"role": "user", "content": "hello"}]) == "hello"
    assert client.calls[0]["options"] == {"temperature": 0.25, "seed": 123}


def test_structured_passes_configured_options():
    client = FakeOllamaClient('{"summary":"wait","action_type":"stop"}')
    llm = OllamaLLM(Settings(temperature=0.4, seed=7), client=client)

    result = llm.structured(
        [{"role": "user", "content": "propose"}],
        ActivityProposal,
    )

    assert result.summary == "wait"
    assert client.calls[0]["options"] == {"temperature": 0.4, "seed": 7}


def test_temperature_must_be_in_supported_range():
    with pytest.raises(ValidationError):
        Settings(temperature=2.5)


def test_seed_is_omitted_when_not_configured():
    client = FakeOllamaClient("hello")
    llm = OllamaLLM(Settings(), client=client)

    llm.chat([{"role": "user", "content": "hello"}])

    assert client.calls[0]["options"] == {"temperature": 0.8}
