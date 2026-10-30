"""Export initiative execution records to a provenance-rich manual review sheet."""
import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


REVIEW_FIELDS = [
    "cycle_id", "proposal", "response", "used_evidence_ids", "valid_evidence_ids",
    "rejected_evidence_ids", "inferences",
    "unknowns", "proposed_checks", "response_status", "action_performed",
    "progress_verified", "verification", "history_accuracy", "evidence_grounding",
    "useful_answer", "check_was_actually_run", "non_repetition", "reviewer_notes",
]


def export_review_sheet(database: Path | str, output: Path | str) -> int:
    """Export reflections without initializing or modifying the source database."""
    db_path = Path(database).resolve()
    uri = f"file:{db_path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        rows = connection.execute(
            "SELECT content FROM events WHERE event_type = 'initiative_result' ORDER BY id"
        ).fetchall()

    records: list[dict[str, Any]] = []
    for (content,) in rows:
        try:
            event = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            continue
        result = event.get("result", "")
        if isinstance(result, dict):
            report = result
        else:  # Legacy event format: keep response reviewable, but mark unknowns explicitly.
            report = {"response": str(result)}
        records.append({
            "cycle_id": event.get("cycle_id", ""),
            "proposal": event.get("summary", ""),
            "response": report.get("response", ""),
            "used_evidence_ids": json.dumps(report.get("used_evidence_ids", []), ensure_ascii=False),
            "valid_evidence_ids": json.dumps(event.get("evidence_validation", {}).get("valid_ids", []), ensure_ascii=False),
            "rejected_evidence_ids": json.dumps(event.get("evidence_validation", {}).get("rejected_ids", []), ensure_ascii=False),
            "inferences": json.dumps(report.get("inferences", []), ensure_ascii=False),
            "unknowns": json.dumps(report.get("unknowns", []), ensure_ascii=False),
            "proposed_checks": json.dumps(report.get("proposed_checks", []), ensure_ascii=False),
            "response_status": event.get("response_status", "received" if event.get("status") == "completed" else "unknown"),
            "action_performed": event.get("action_performed", "reflection_call" if event.get("status") == "completed" else "unknown"),
            "progress_verified": event.get("progress_verified", False),
            "verification": event.get("verification") or "none recorded",
            "history_accuracy": "", "evidence_grounding": "", "useful_answer": "",
            "check_was_actually_run": "", "non_repetition": "", "reviewer_notes": "",
        })

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="SQLite experiment database (opened read-only)")
    parser.add_argument("output", type=Path, help="CSV path for manual review")
    args = parser.parse_args()
    count = export_review_sheet(args.database, args.output)
    print(f"Exported {count} initiative results to {args.output}")


if __name__ == "__main__":
    main()
