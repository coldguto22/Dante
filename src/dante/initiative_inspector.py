"""Fixed, read-only queries for isolated initiative experiment databases."""
import json
import sqlite3
from pathlib import Path
from typing import Any

from dante.models import EventLogInspectionRequest


class EventLogInspector:
    """Execute only bounded, parameterized event-log queries."""

    def __init__(
        self,
        database: Path | str,
        *,
        main_database: Path | str = Path("data/dante.sqlite3"),
    ) -> None:
        self.database = Path(database).resolve()
        self.main_database = Path(main_database).resolve()

    def _is_main_database(self) -> bool:
        if self.database == self.main_database:
            return True
        try:
            return self.database.samefile(self.main_database)
        except (FileNotFoundError, OSError):
            return False

    def inspect(self, request: EventLogInspectionRequest) -> dict[str, Any]:
        if self._is_main_database():
            raise ValueError("The main conversation database is not an initiative experiment database.")
        if not self.database.is_file():
            raise FileNotFoundError(f"Experiment database does not exist: {self.database}")
        uri = f"file:{self.database.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            if request.query == "event_counts":
                rows = connection.execute(
                    "SELECT event_type, COUNT(*) AS count "
                    "FROM events GROUP BY event_type ORDER BY event_type"
                ).fetchall()
                return {"query": request.query, "counts": [
                    {"event_type": str(event_type), "count": int(count)}
                    for event_type, count in rows
                ]}
            if request.query == "recent_results":
                rows = connection.execute(
                    "SELECT content FROM events WHERE event_type = 'initiative_result' "
                    "ORDER BY id DESC LIMIT ?", (request.limit,)
                ).fetchall()
                return {"query": request.query, "results": [
                    self._result_summary(content) for (content,) in rows
                ]}
            if request.query == "cycle_result":
                found = connection.execute(
                    "SELECT 1 FROM events WHERE event_type = 'initiative_result' "
                    "AND json_extract(content, '$.cycle_id') = ? LIMIT 1",
                    (request.cycle_id,),
                ).fetchone() is not None
                return {"query": request.query, "cycle_id": request.cycle_id, "has_result": found}
            rows = connection.execute(
                "SELECT content FROM events WHERE event_type = 'initiative_decision' "
                "ORDER BY id DESC LIMIT ?", (request.limit,)
            ).fetchall()
            return {"query": request.query, "decisions": [
                self._decision_summary(content) for (content,) in rows
            ]}

    @staticmethod
    def _result_summary(content: str) -> dict[str, Any]:
        try:
            payload = json.loads(content)
        except (TypeError, ValueError):
            return {"status": "malformed"}
        return {
            "cycle_id": str(payload.get("cycle_id", "")),
            "action_type": str(payload.get("action_type", "")),
            "status": str(payload.get("status", "")),
            "summary": str(payload.get("summary", ""))[:500],
        }

    @staticmethod
    def _decision_summary(content: str) -> dict[str, Any]:
        try:
            payload = json.loads(content)
        except (TypeError, ValueError):
            return {"status": "malformed"}
        return {
            "cycle_id": str(payload.get("cycle_id", "")),
            "decision": str(payload.get("decision", "")),
            "action_type": str(payload.get("action_type", "")),
            "summary": str(payload.get("summary", ""))[:500],
        }
