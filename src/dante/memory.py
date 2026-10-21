"""Minimal SQLite event persistence."""
import json
import sqlite3
from pathlib import Path

from dante.models import AgentEvent


class EventStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

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

    def recent(self, limit: int = 20) -> list[AgentEvent]:
        if limit < 1:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT timestamp, event_type, content, metadata_json "
                "FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        rows.reverse()
        return [
            AgentEvent(timestamp=row[0], event_type=row[1], content=row[2],
                       metadata=json.loads(row[3]))
            for row in rows
        ]
