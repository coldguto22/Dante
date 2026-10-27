"""Read-only diagnostics for Dante's current SQLite conversation memory.

Run with: python -m dante.memory_audit
This module never writes to the database.
"""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from dante.config import get_settings

CONTEXT_EVENT_LIMIT = 12
CONVERSATION_EVENT_TYPES = {"user_message", "assistant_message"}


def _connect(db_path: Path) -> sqlite3.Connection:
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
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
        with closing(_connect(resolved_path)) as connection:
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
                "SELECT id, timestamp, event_type, content FROM events "
                "WHERE event_type IN ('user_message', 'assistant_message') "
                "ORDER BY id DESC LIMIT ?",
                (CONTEXT_EVENT_LIMIT,),
            ).fetchall()
            recent = list(reversed(recent))
            print(f"\nLast {CONTEXT_EVENT_LIMIT} conversation messages "
                  "(snapshot before the next user message is added):")
            if not recent:
                print("  (none)")
            for row in recent:
                preview = row["content"].replace("\n", " ")
                if len(preview) > 180:
                    preview = preview[:177] + "..."
                print(f"  #{row['id']} {row['event_type']} — eligible for LLM context")
                print(f"    {preview}")

            if show_context:
                print("\nConversation messages assembled from this snapshot:")
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
            print("  - The agent selects the last 12 user/assistant messages, filtering event types in SQL before applying the limit.")
            print("  - Initiative proposals and decisions remain in the audit log but do not consume conversation-context slots.")
            print("  - The next turn adds the new user message before selecting its 12-message conversation window.")
            print("  - This report cannot establish whether the model used retrieved information correctly.")
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
        help="Print full user/assistant message contents selected from the event window.",
    )
    args = parser.parse_args()
    raise SystemExit(audit_database(get_settings().db_path, args.search, args.show_context))


if __name__ == "__main__":
    main()
