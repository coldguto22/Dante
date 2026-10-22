import json

from dante.agent import DanteAgent
from dante.config import Settings
from dante.memory import EventStore
from dante.models import AgentEvent


class RecordingLLM:
    def __init__(self):
        self.messages = []

    def chat(self, messages):
        self.messages = messages
        return "Test response"


def test_context_trace_records_ids_and_fingerprints_without_message_text(tmp_path, monkeypatch):
    trace_path = tmp_path / "diagnostics" / "context.jsonl"
    monkeypatch.setenv("DANTE_CONTEXT_TRACE_PATH", str(trace_path))
    settings = Settings(db_path=tmp_path / "events.sqlite3")
    store = EventStore(settings.db_path)
    private_text = "My test name is Otavio-Secret-914"
    llm = RecordingLLM()
    agent = DanteAgent(settings, llm=llm, store=store)

    agent.respond(private_text)

    trace_line = trace_path.read_text(encoding="utf-8").strip()
    trace = json.loads(trace_line)
    assert private_text not in trace_line
    assert trace["events"][0]["event_type"] == "user_message"
    assert trace["events"][0]["included_in_llm_context"] is True
    assert trace["events"][0]["content"]["characters"] == len(private_text)
    assert trace["events"][0]["content"]["sha256"]
    assert trace["events"][0]["event_id"] == 1
    assert trace["llm_messages"][1]["role"] == "user"
    assert trace["llm_messages"][1]["content"]["characters"] == len(private_text)


def test_context_trace_marks_filtered_event_types(tmp_path, monkeypatch):
    trace_path = tmp_path / "context.jsonl"
    monkeypatch.setenv("DANTE_CONTEXT_TRACE_PATH", str(trace_path))
    settings = Settings(db_path=tmp_path / "events.sqlite3")
    store = EventStore(settings.db_path)
    store.add(AgentEvent(event_type="proposal", content="private proposal text"))
    llm = RecordingLLM()
    agent = DanteAgent(settings, llm=llm, store=store)

    agent.respond("What do you remember?")

    trace = json.loads(trace_path.read_text(encoding="utf-8").strip())
    proposal = next(item for item in trace["events"] if item["event_type"] == "proposal")
    assert proposal["included_in_llm_context"] is False
    assert proposal["excluded_reason"] == "event_type_filtered"
    assert "private proposal text" not in trace_path.read_text(encoding="utf-8")


def test_event_store_recent_with_ids_preserves_chronological_order(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    first_id = store.add(AgentEvent(event_type="user_message", content="first"))
    second_id = store.add(AgentEvent(event_type="assistant_message", content="second"))

    records = store.recent_with_ids(limit=2)
    assert [event_id for event_id, _ in records] == [first_id, second_id]
    assert [event.content for _, event in records] == ["first", "second"]
