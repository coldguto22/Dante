from dante.agent import DanteAgent
from dante.config import Settings
from dante.memory import EventStore


class RecordingLLM:
    def __init__(self):
        self.messages = []

    def chat(self, messages):
        self.messages = messages
        return "Recorded response"


def test_agent_context_is_limited_to_latest_twelve_stored_events(tmp_path):
    settings = Settings(db_path=tmp_path / "window.sqlite3")
    llm = RecordingLLM()
    agent = DanteAgent(settings, llm=llm, store=EventStore(settings.db_path))

    for index in range(1, 8):
        agent.respond(f"Question {index}")

    user_messages = [
        message["content"]
        for message in llm.messages
        if message["role"] == "user"
    ]

    # Seven exchanges create fourteen events. The last twelve stored events
    # omit both events from the first exchange.
    assert "Question 1" not in user_messages
    assert "Question 2" in user_messages
    assert "Question 7" in user_messages
    assert len(user_messages) == 6
