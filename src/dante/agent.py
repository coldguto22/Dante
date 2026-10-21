"""Conversation orchestration with explicit logging and no tool execution."""
from dante.config import Settings
from dante.llm import OllamaLLM
from dante.memory import EventStore
from dante.models import AgentEvent, Message


class DanteAgent:
    def __init__(self, settings: Settings, llm: OllamaLLM | None = None,
                 store: EventStore | None = None) -> None:
        self.settings = settings
        self.llm = llm or OllamaLLM(settings)
        self.store = store or EventStore(settings.db_path)

    def respond(self, user_text: str) -> str:
        user_message = Message(role="user", content=user_text.strip())
        self.store.add(AgentEvent(event_type="user_message", content=user_message.content))

        history = self.store.recent(limit=12)
        messages = [{"role": "system", "content": self.settings.system_prompt}]
        for event in history:
            if event.event_type == "user_message":
                messages.append({"role": "user", "content": event.content})
            elif event.event_type == "assistant_message":
                messages.append({"role": "assistant", "content": event.content})

        try:
            answer = self.llm.chat(messages)
        except Exception as exc:
            self.store.add(AgentEvent(event_type="error", content=str(exc),
                                      metadata={"component": "llm"}))
            raise

        self.store.add(AgentEvent(event_type="assistant_message", content=answer))
        return answer
