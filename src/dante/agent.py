"""Conversation orchestration with optional privacy-preserving context tracing."""
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from dante.config import Settings
from dante.llm import OllamaLLM
from dante.memory import EventStore
from dante.models import AgentEvent, Message

# A per-process secret prevents the trace fingerprints from being used as a simple
# dictionary oracle for predictable messages such as names or short phrases.
_TRACE_HMAC_KEY = secrets.token_bytes(32)


class DanteAgent:
    def __init__(self, settings: Settings, llm: OllamaLLM | None = None,
                 store: EventStore | None = None) -> None:
        self.settings = settings
        self.llm = llm or OllamaLLM(settings)
        self.store = store or EventStore(settings.db_path)

    @staticmethod
    def _fingerprint(content: str) -> dict[str, int | str]:
        """Describe content without storing it or exposing an unkeyed content hash."""
        fingerprint = hmac.new(
            _TRACE_HMAC_KEY, content.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return {
            "characters": len(content),
            "hmac_sha256": fingerprint,
        }

    def _trace_context(
        self,
        selected: list[tuple[int, AgentEvent]],
        messages: list[dict[str, str]],
    ) -> None:
        """Append a metadata-only trace when DANTE_CONTEXT_TRACE_PATH is configured."""
        raw_path = os.getenv("DANTE_CONTEXT_TRACE_PATH")
        if not raw_path:
            return

        included_types = {"user_message", "assistant_message"}
        message_index = 1  # Index zero is always the system prompt.
        events = []
        for event_id, event in selected:
            included = event.event_type in included_types
            record: dict[str, object] = {
                "event_id": event_id,
                "event_type": event.event_type,
                "included_in_llm_context": included,
                "content": self._fingerprint(event.content),
            }
            if included:
                record["message_index"] = message_index
                message_index += 1
            else:
                record["excluded_reason"] = "event_type_filtered"
            events.append(record)

        trace = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": self.settings.model,
            "database_path": str(self.settings.db_path),
            "selected_event_ids": [event_id for event_id, _ in selected],
            "system_prompt": self._fingerprint(messages[0]["content"]),
            "events": events,
            "llm_messages": [
                {"index": index, "role": message["role"],
                 "content": self._fingerprint(message["content"])}
                for index, message in enumerate(messages)
            ],
        }
        path = Path(raw_path).expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(trace, ensure_ascii=False) + "\n")
        except OSError:
            # Diagnostics must never prevent a normal response.
            return

    def respond(self, user_text: str) -> str:
        user_message = Message(role="user", content=user_text.strip())
        self.store.add(AgentEvent(event_type="user_message", content=user_message.content))

        selected = self.store.recent_with_ids(limit=12)
        messages = [{"role": "system", "content": self.settings.system_prompt}]
        for _, event in selected:
            if event.event_type == "user_message":
                messages.append({"role": "user", "content": event.content})
            elif event.event_type == "assistant_message":
                messages.append({"role": "assistant", "content": event.content})

        self._trace_context(selected, messages)

        try:
            answer = self.llm.chat(messages)
        except Exception as exc:
            self.store.add(AgentEvent(event_type="error", content=str(exc),
                                      metadata={"component": "llm"}))
            raise

        self.store.add(AgentEvent(event_type="assistant_message", content=answer))
        return answer
