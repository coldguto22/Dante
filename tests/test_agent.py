from dante.agent import DanteAgent
from dante.config import Settings
from dante.memory import EventStore


class FakeLLM:
    def __init__(self, answer="Hello from a fake model"):
        self.answer = answer
        self.seen_messages = None

    def chat(self, messages):
        self.seen_messages = messages
        return self.answer


def test_agent_records_user_and_assistant_messages(tmp_path):
    settings = Settings(db_path=tmp_path / "agent.sqlite3")
    llm = FakeLLM()
    store = EventStore(settings.db_path)
    agent = DanteAgent(settings, llm=llm, store=store)

    assert agent.respond("Hello") == "Hello from a fake model"
    events = store.recent()
    assert [event.event_type for event in events] == ["user_message", "assistant_message"]
    assert events[-1].content == "Hello from a fake model"


def test_agent_includes_recent_conversation_context(tmp_path):
    settings = Settings(db_path=tmp_path / "agent.sqlite3")
    llm = FakeLLM("Second answer")
    agent = DanteAgent(settings, llm=llm, store=EventStore(settings.db_path))
    agent.respond("First question")
    agent.respond("Second question")

    assert any(
        message["role"] == "user" and message["content"] == "First question"
        for message in llm.seen_messages
    )
