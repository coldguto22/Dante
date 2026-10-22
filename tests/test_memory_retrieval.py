from dante.agent import DanteAgent
from dante.config import Settings
from dante.memory import EventStore
from dante.models import AgentEvent


class RecordingLLM:
    def __init__(self, answer="Recorded response"):
        self.messages = []
        self.answer = answer

    def chat(self, messages):
        self.messages = messages
        return self.answer


def test_retrieves_old_user_authored_name_outside_recent_window(tmp_path):
    settings = Settings(db_path=tmp_path / "retrieval.sqlite3")
    store = EventStore(settings.db_path)
    fact_id = store.add(AgentEvent(
        event_type="user_message", content="Meu nome é Otávio."
    ))
    # Add enough events to move the original statement outside the 12-event window.
    for index in range(8):
        store.add(AgentEvent(event_type="user_message", content=f"Assunto sem relação {index}"))
        store.add(AgentEvent(event_type="assistant_message", content=f"Resposta {index}"))

    llm = RecordingLLM()
    agent = DanteAgent(settings, llm=llm, store=store)
    agent.respond("Dante, você lembra qual é meu nome?")

    recovered = next(
        message for message in llm.messages
        if message["role"] == "system" and "Memórias recuperadas" in message["content"]
    )
    assert f"evento #{fact_id}" in recovered["content"]
    assert "Meu nome é Otávio." in recovered["content"]


def test_retrieval_does_not_promote_assistant_hallucinations(tmp_path):
    store = EventStore(tmp_path / "retrieval.sqlite3")
    store.add(AgentEvent(
        event_type="assistant_message",
        content="Seu nome é Otávio e você inventou o violino azul.",
    ))
    store.add(AgentEvent(
        event_type="user_message", content="Meu instrumento favorito é o violino azul."
    ))

    results = store.search_user_messages("qual é meu nome?", limit=5)
    assert results == []


def test_retrieval_returns_no_results_without_token_overlap(tmp_path):
    store = EventStore(tmp_path / "retrieval.sqlite3")
    store.add(AgentEvent(event_type="user_message", content="Gosto de tocar guitarra."))
    assert store.search_user_messages("qual é a capital do Japão?") == []
