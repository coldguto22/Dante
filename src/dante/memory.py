"""Minimal SQLite event persistence and retrieval of user-authored memories."""
import json
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dante.models import AgentEvent


_STOP_WORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "é", "em", "essa", "esse", "esta", "este", "eu", "foi", "isso",
    "isto", "me", "meu", "minha", "nas", "no", "nos", "o", "os", "ou",
    "para", "pela", "pelas", "pelo", "pelos", "por", "qual", "quando",
    "que", "quem", "se", "sou", "sua", "suas", "te", "um", "uma", "você",
}


def _tokens(text: str) -> set[str]:
    """Normalize words for a small, dependency-free lexical retrieval baseline."""
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return {
        token for token in re.findall(r"[a-z0-9]+", normalized)
        if len(token) > 1 and token not in _STOP_WORDS
    }


class EventStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection and always close it after committing or rolling back."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
            """)

    def add(self, event: AgentEvent) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO events (timestamp, event_type, content, metadata_json) "
                "VALUES (?, ?, ?, ?)",
                (event.timestamp.isoformat(), event.event_type, event.content,
                 json.dumps(event.metadata, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    @staticmethod
    def _event_from_row(row: tuple) -> tuple[int, AgentEvent]:
        return (
            int(row[0]),
            AgentEvent(timestamp=row[1], event_type=row[2], content=row[3],
                       metadata=json.loads(row[4])),
        )

    def recent_with_ids(self, limit: int = 20) -> list[tuple[int, AgentEvent]]:
        """Return recent events with stable database IDs, in chronological order."""
        if limit < 1:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, event_type, content, metadata_json "
                "FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        rows.reverse()
        return [self._event_from_row(row) for row in rows]

    def recent_conversation_with_ids(self, limit: int = 12) -> list[tuple[int, AgentEvent]]:
        """Return the latest conversation messages, ignoring internal event types.

        The limit applies after filtering to user/assistant messages, so initiative
        proposals and diagnostics cannot consume conversational context slots.
        Results are returned in chronological order.
        """
        if limit < 1:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, event_type, content, metadata_json "
                "FROM events "
                "WHERE event_type IN ('user_message', 'assistant_message') "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        rows.reverse()
        return [self._event_from_row(row) for row in rows]

    def search_user_messages(
        self,
        query: str,
        limit: int = 3,
        exclude_event_id: int | None = None,
        exclude_event_ids: set[int] | None = None,
    ) -> list[tuple[int, AgentEvent]]:
        """Find user-authored messages by token overlap, newest first on ties.

        Exclusions are applied before ranking and truncating to the top-k results,
        so recent events cannot occupy retrieval slots only to be discarded later.
        Assistant replies are intentionally excluded: model-generated claims are not
        promoted into user facts merely because they were saved in the event log.
        This is a lexical baseline, not semantic search or a verified fact store.
        """
        query_tokens = _tokens(query)
        if not query_tokens or limit < 1:
            return []

        excluded_ids = set(exclude_event_ids or ())
        if exclude_event_id is not None:
            excluded_ids.add(exclude_event_id)

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, event_type, content, metadata_json "
                "FROM events WHERE event_type = 'user_message' ORDER BY id DESC"
            ).fetchall()

        scored: list[tuple[int, float, AgentEvent]] = []
        for row in rows:
            event_id, event = self._event_from_row(row)
            if event_id in excluded_ids:
                continue
            overlap = query_tokens & _tokens(event.content)
            if overlap:
                score = len(overlap) / len(query_tokens)
                scored.append((event_id, score, event))

        scored.sort(key=lambda item: (item[1], item[0]), reverse=True)
        return [(event_id, event) for event_id, _, event in scored[:limit]]

    def recent(self, limit: int = 20) -> list[AgentEvent]:
        """Return recent events in chronological order, preserving the existing API."""
        return [event for _, event in self.recent_with_ids(limit)]
