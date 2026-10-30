import csv
import json
import sqlite3

from dante.initiative_eval import export_review_sheet


def test_export_review_sheet_separates_claims_from_execution_and_progress(tmp_path):
    database = tmp_path / "experiment.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE events (id INTEGER PRIMARY KEY, event_type TEXT, content TEXT)"
        )
        payload = {
            "cycle_id": "cycle-1", "summary": "Review prior result", "status": "completed",
            "response_status": "received", "action_performed": True,
            "progress_verified": False, "verification": None,
            "evidence_validation": {"valid_ids": ["result:cycle-0"], "rejected_ids": ["result:fake"]},
            "result": {
                "response": "The prior output suggests a limitation.",
                "used_evidence_ids": ["result:cycle-0"],
                "inferences": ["The limitation may matter."],
                "unknowns": ["Whether it affects selection."],
                "proposed_checks": ["Compare next selection with baseline."],
            },
        }
        connection.execute(
            "INSERT INTO events(event_type, content) VALUES (?, ?)",
            ("initiative_result", json.dumps(payload)),
        )
        connection.execute(
            "INSERT INTO events(event_type, content) VALUES (?, ?)",
            ("user_message", "must not be exported"),
        )

    output = tmp_path / "review.csv"
    assert export_review_sheet(database, output) == 1
    with output.open(encoding="utf-8-sig", newline="") as file:
        row = next(csv.DictReader(file))

    assert row["response_status"] == "received"
    assert row["action_performed"] == "True"
    assert row["progress_verified"] == "False"
    assert row["verification"] == "none recorded"
    assert json.loads(row["used_evidence_ids"]) == ["result:cycle-0"]
    assert json.loads(row["valid_evidence_ids"]) == ["result:cycle-0"]
    assert json.loads(row["rejected_evidence_ids"]) == ["result:fake"]
    assert row["proposed_checks"]
    assert row["check_was_actually_run"] == ""
    assert row["history_accuracy"] == ""
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2


def test_export_review_sheet_supports_legacy_text_result(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE events (id INTEGER, event_type TEXT, content TEXT)")
        connection.execute(
            "INSERT INTO events VALUES (1, 'initiative_result', ?)",
            (json.dumps({"cycle_id": "old", "status": "completed", "result": "Old result"}),),
        )
    output = tmp_path / "legacy.csv"
    assert export_review_sheet(database, output) == 1
    with output.open(encoding="utf-8-sig", newline="") as file:
        row = next(csv.DictReader(file))
    assert row["response"] == "Old result"
    assert row["progress_verified"] == "False"
