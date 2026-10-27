from dante.agent import DanteAgent
from dante.config import Settings
from dante.memory import EventStore
from dante.models import AgentEvent


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
    assert events[0].metadata["session_id"] == agent.session_id
    assert events[1].metadata["session_id"] == agent.session_id


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


def test_agent_recovers_old_fact_when_recent_questions_fill_top_k(tmp_path):
    settings = Settings(db_path=tmp_path / "agent.sqlite3")
    store = EventStore(settings.db_path)
    store.add(AgentEvent(
        event_type="user_message",
        content="Minha gata Alicia gosta de perseguir bolinhas de papel.",
        metadata={"session_id": "old-session"},
    ))

    for index in range(3):
        store.add(AgentEvent(event_type="user_message", content=f"Assunto aleatorio {index}"))
        store.add(AgentEvent(event_type="assistant_message", content=f"Resposta aleatoria {index}"))

    for question in (
        "Será que a gata Alicia gosta de bolinhas de papel?",
        "Por que a gata Alicia gosta de bolinhas de papel?",
        "Quando a gata Alicia gosta de fazer bolinhas de papel?",
    ):
        store.add(AgentEvent(event_type="user_message", content=question))
        store.add(AgentEvent(event_type="assistant_message", content="Não tenho certeza."))

    llm = FakeLLM("Ela gosta de perseguir bolinhas de papel.")
    agent = DanteAgent(settings, llm=llm, store=store)
    agent.respond("O que a gata Alicia gosta de fazer com bolinhas de papel?")

    recovered_context = next(
        message["content"] for message in llm.seen_messages
        if message["role"] == "system" and "Memórias recuperadas" in message["content"]
    )
    assert "perseguir bolinhas de papel" in recovered_context
    assert "sessão=old-session" in recovered_context
    assert "data=" in recovered_context


def test_agent_context_keeps_twelve_conversation_messages_despite_internal_events(tmp_path):
    settings = Settings(db_path=tmp_path / "agent.sqlite3")
    store = EventStore(settings.db_path)
    for index in range(8):
        store.add(AgentEvent(event_type="user_message", content=f"user-{index}"))
        store.add(AgentEvent(event_type="assistant_message", content=f"assistant-{index}"))
        store.add(AgentEvent(event_type="proposal", content=f"internal proposal {index}"))
        store.add(AgentEvent(event_type="initiative_decision", content=f"internal decision {index}"))

    llm = FakeLLM("New answer")
    agent = DanteAgent(settings, llm=llm, store=store)
    agent.respond("new question")

    conversation = [
        message for message in llm.seen_messages
        if message["role"] in {"user", "assistant"}
    ]
    assert len(conversation) == 12
    assert conversation[0]["content"] == "user-2"
    assert conversation[-1]["content"] == "new question"
    assert not any("internal proposal" in message["content"] for message in llm.seen_messages)
