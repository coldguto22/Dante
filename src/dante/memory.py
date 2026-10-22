"""Minimal SQLite event persistence."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dante.models import AgentEvent


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
        return [
            (
                int(row[0]),
                AgentEvent(timestamp=row[1], event_type=row[2], content=row[3],
                           metadata=json.loads(row[4])),
            )
            for row in rows
        ]

    def recent(self, limit: int = 20) -> list[AgentEvent]:
        """Return recent events in chronological order, preserving the existing API."""
        return [event for _, event in self.recent_with_ids(limit)]
