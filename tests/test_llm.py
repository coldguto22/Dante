from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from dante.config import Settings
from dante.llm import LLMError, OllamaLLM
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
    assert client.calls[0]["options"] == {
        "temperature": 0.25, "seed": 123, "num_ctx": 2048
    }


def test_structured_passes_configured_options():
    client = FakeOllamaClient(
        '{"summary":"wait","rationale":"It ends the cycle.","action_type":"stop"}'
    )
    llm = OllamaLLM(Settings(temperature=0.4, seed=7), client=client)

    result = llm.structured(
        [{"role": "user", "content": "propose"}],
        ActivityProposal,
    )

    assert result.summary == "wait"
    assert client.calls[0]["options"] == {
        "temperature": 0.4, "seed": 7, "num_ctx": 2048
    }


def test_structured_uses_base_temperature_by_default_even_when_reflection_override_exists():
    client = FakeOllamaClient(
        '{"summary":"wait","rationale":"It ends the cycle.","action_type":"stop"}'
    )
    settings = Settings(
        temperature=0.8, reflection_temperature=0.25, num_ctx=4096, seed=7
    )
    llm = OllamaLLM(settings, client=client)

    llm.structured([{"role": "user", "content": "propose"}], ActivityProposal)

    assert client.calls[0]["options"] == {
        "temperature": 0.8, "seed": 7, "num_ctx": 4096
    }
    assert llm.last_telemetry["telemetry_status"] == "unavailable"


def test_structured_accepts_explicit_reflection_temperature():
    client = FakeOllamaClient(
        '{"summary":"wait","rationale":"It ends the cycle.","action_type":"stop"}'
    )
    llm = OllamaLLM(Settings(temperature=0.8, seed=7, num_ctx=4096), client=client)

    llm.structured(
        [{"role": "user", "content": "reflect"}],
        ActivityProposal,
        temperature=0.25,
    )

    assert client.calls[0]["options"] == {
        "temperature": 0.25, "seed": 7, "num_ctx": 4096
    }


def test_temperature_must_be_in_supported_range():
    with pytest.raises(ValidationError):
        Settings(temperature=2.5)


def test_seed_is_omitted_when_not_configured():
    client = FakeOllamaClient("hello")
    llm = OllamaLLM(Settings(), client=client)

    llm.chat([{"role": "user", "content": "hello"}])

    assert client.calls[0]["options"] == {"temperature": 0.8, "num_ctx": 2048}


def test_chat_error_preserves_ollama_failure_cause():
    class FailingClient:
        def chat(self, **kwargs):
            raise RuntimeError("llama-server reported out-of-memory during startup")

    llm = OllamaLLM(Settings(model="llama3.1:8b"), client=FailingClient())

    with pytest.raises(LLMError, match="llama3.1:8b.*out-of-memory"):
        llm.chat([{"role": "user", "content": "hello"}])
