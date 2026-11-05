import sqlite3

import pytest
from pydantic import ValidationError

from dante.initiative_inspector import EventLogInspector
from dante.models import EventLogInspectionRequest


def _database(path):
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE events (id INTEGER PRIMARY KEY, event_type TEXT, content TEXT, metadata_json TEXT)"
        )
        connection.executemany(
            "INSERT INTO events VALUES (?, ?, ?, ?)",
            [
                (1, "initiative_decision", '{"cycle_id":"c1","decision":"selected","action_type":"reflect","summary":"one"}', "{}"),
                (2, "initiative_result", '{"cycle_id":"c1","status":"completed","action_type":"reflect","summary":"one","result":"private"}', "{}"),
                (3, "initiative_result", '{"cycle_id":"c2","status":"error","action_type":"reflect","summary":"two","result":"private"}', "{}"),
                (4, "user_message", "secret conversation", "{}"),
            ],
        )


def test_request_schema_has_fixed_queries_and_hard_bounds():
    assert EventLogInspectionRequest(query="event_counts").limit == 5
    with pytest.raises(ValidationError):
        EventLogInspectionRequest(query="recent_results", limit=0)
    with pytest.raises(ValidationError):
        EventLogInspectionRequest(query="recent_results", limit=11)
    with pytest.raises(ValidationError):
        EventLogInspectionRequest(query="cycle_result")
    with pytest.raises(ValidationError):
        EventLogInspectionRequest(query="event_counts", cycle_id="c1")
    with pytest.raises(ValidationError):
        EventLogInspectionRequest(query="not_sql")  # type: ignore[arg-type]


def test_inspector_runs_bounded_read_only_queries_without_result_text(tmp_path):
    database = tmp_path / "initiative.sqlite3"
    _database(database)
    inspector = EventLogInspector(database)

    assert inspector.inspect(EventLogInspectionRequest(query="event_counts"))["counts"]
    results = inspector.inspect(EventLogInspectionRequest(query="recent_results", limit=1))
    assert len(results["results"]) == 1
    assert all("result" not in item for item in results["results"])
    assert inspector.inspect(EventLogInspectionRequest(query="cycle_result", cycle_id="c1"))["has_result"]
    decisions = inspector.inspect(EventLogInspectionRequest(query="recent_decisions", limit=1))
    assert len(decisions["decisions"]) == 1

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 4


def test_inspector_rejects_main_database_and_missing_database(tmp_path):
    with pytest.raises(ValueError, match="main conversation"):
        EventLogInspector(
            tmp_path / "conversation-renamed.sqlite3",
            main_database=tmp_path / "conversation-renamed.sqlite3",
        ).inspect(
            EventLogInspectionRequest(query="event_counts")
        )
    main_database = tmp_path / "main-with-custom-name.sqlite3"
    _database(main_database)
    with pytest.raises(ValueError, match="main conversation"):
        EventLogInspector(
            tmp_path / "." / main_database.name, main_database=main_database
        ).inspect(EventLogInspectionRequest(query="event_counts"))
    with pytest.raises(FileNotFoundError):
        EventLogInspector(tmp_path / "experiment.sqlite3").inspect(
            EventLogInspectionRequest(query="event_counts")
        )
