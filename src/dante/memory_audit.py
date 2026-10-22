"""Read-only diagnostics for Dante's current SQLite conversation memory.

Run with: python -m dante.memory_audit
This module never writes to the database.
"""
import argparse
import json
import sqlite3
from pathlib import Path

from dante.config import get_settings

CONTEXT_EVENT_LIMIT = 12
CONVERSATION_EVENT_TYPES = {"user_message", "assistant_message"}


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def audit_database(db_path: Path, search: str | None = None,
                   show_context: bool = False) -> int:
    """Print a read-only summary of the database; return a process status code."""
    if str(db_path) == ":memory:":
        print("Configured database is in-memory and cannot be inspected from a separate process.")
        return 2
    resolved_path = db_path.expanduser().resolve()
    print(f"Database: {resolved_path}")
    if not resolved_path.is_file():
        print("Status: database file does not exist.")
        print("No database was created or modified by this diagnostic.")
        return 1

    try:
        with _connect(resolved_path) as connection:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
            ).fetchone()
            if table is None:
                print("Status: no 'events' table found.")
                return 1

            counts = connection.execute(
                "SELECT event_type, COUNT(*) AS total FROM events "
                "GROUP BY event_type ORDER BY event_type"
            ).fetchall()
            total = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            print(f"Total events: {total}")
            print("Events by type:")
            if counts:
                for row in counts:
                    print(f"  {row['event_type']}: {row['total']}")
            else:
                print("  (none)")

            if search:
                matches = connection.execute(
                    "SELECT id, timestamp, event_type, content FROM events "
                    "WHERE instr(lower(content), lower(?)) > 0 ORDER BY id",
                    (search,),
                ).fetchall()
                print(f"\nSearch matches for {search!r}: {len(matches)}")
                for row in matches:
                    print(f"  #{row['id']} [{row['timestamp']}] {row['event_type']}:")
                    print(f"    {row['content']}")

            recent = connection.execute(
                "SELECT id, timestamp, event_type, content, metadata_json FROM events "
                "ORDER BY id DESC LIMIT ?",
                (CONTEXT_EVENT_LIMIT,),
            ).fetchall()
            recent = list(reversed(recent))
            print(f"\nLast {CONTEXT_EVENT_LIMIT} stored events "
                  f"(the current agent's retrieval window):")
            if not recent:
                print("  (none)")
            for row in recent:
                preview = row["content"].replace("\n", " ")
                if len(preview) > 180:
                    preview = preview[:177] + "..."
                included = row["event_type"] in CONVERSATION_EVENT_TYPES
                marker = "sent to LLM" if included else "stored, filtered from LLM context"
                print(f"  #{row['id']} {row['event_type']} — {marker}")
                print(f"    {preview}")

            if show_context:
                print("\nConversation messages assembled from that window:")
                messages = [
                    {"role": "user" if row["event_type"] == "user_message" else "assistant",
                     "content": row["content"]}
                    for row in recent
                    if row["event_type"] in CONVERSATION_EVENT_TYPES
                ]
                if not messages:
                    print("  (none)")
                for message in messages:
                    print(f"  [{message['role']}] {message['content']}")

            print("\nNotes:")
            print("  - The agent selects the last 12 stored events, not the last 12 conversation messages.")
            print("  - Non-conversation events can consume slots in that window and are then filtered out.")
            print("  - This report shows stored/retrieved context, not whether the model used it correctly.")
            return 0
    except sqlite3.Error as exc:
        print(f"SQLite read error: {exc}")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only audit of Dante's configured SQLite event memory."
    )
    parser.add_argument(
        "--search",
        help="Case-insensitive text to find across stored event content (for example, a name).",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Print full user/assistant message contents selected for the LLM context.",
    )
    args = parser.parse_args()
    raise SystemExit(audit_database(get_settings().db_path, args.search, args.show_context))


if __name__ == "__main__":
    main()
