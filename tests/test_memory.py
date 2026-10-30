import pytest

from dante.memory import EventStore
from dante.models import AgentEvent


def test_event_store_round_trip(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    event = AgentEvent(event_type="user_message", content="Hello Dante",
                       metadata={"source": "test", "count": 1})
    store.add(event)
    events = store.recent()
    assert len(events) == 1
    assert events[0].event_type == "user_message"
    assert events[0].content == "Hello Dante"
    assert events[0].metadata == {"source": "test", "count": 1}


def test_recent_limit_returns_latest_events(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    store.add(AgentEvent(event_type="user_message", content="first"))
    store.add(AgentEvent(event_type="assistant_message", content="second"))
    events = store.recent(limit=1)
    assert len(events) == 1
    assert events[0].content == "second"


def test_non_positive_limit_returns_empty_list(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    assert store.recent(limit=0) == []


def test_retrieval_excludes_recent_ids_before_applying_top_k(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    old_id = store.add(AgentEvent(
        event_type="user_message",
        content="Minha gata Alicia gosta de perseguir bolinhas de papel.",
        metadata={"session_id": "old-session"},
    ))
    recent_ids = set()
    for question in (
        "Será que a gata Alicia gosta de bolinhas de papel?",
        "Por que a gata Alicia gosta de bolinhas de papel?",
        "Quando a gata Alicia gosta de fazer bolinhas de papel?",
    ):
        recent_ids.add(store.add(AgentEvent(event_type="user_message", content=question)))

    results = store.search_user_messages(
        "O que a gata Alicia gosta de fazer com bolinhas de papel?",
        limit=3,
        exclude_event_ids=recent_ids,
    )

    assert results
    assert results[0][0] == old_id
    assert "perseguir bolinhas de papel" in results[0][1].content


def test_recent_conversation_limit_ignores_internal_events(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    for index in range(8):
        store.add(AgentEvent(event_type="user_message", content=f"user-{index}"))
        store.add(AgentEvent(event_type="assistant_message", content=f"assistant-{index}"))
        store.add(AgentEvent(event_type="proposal", content=f"proposal-{index}"))
        store.add(AgentEvent(event_type="initiative_decision", content=f"decision-{index}"))

    selected = store.recent_conversation_with_ids(limit=12)
    assert len(selected) == 12
    assert all(event.event_type in {"user_message", "assistant_message"} for _, event in selected)
    assert [event.content for _, event in selected] == [
        item for index in range(2, 8) for item in (f"user-{index}", f"assistant-{index}")
    ]


def test_recent_conversation_non_positive_limit_returns_empty(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    store.add(AgentEvent(event_type="user_message", content="hello"))
    assert store.recent_conversation_with_ids(limit=0) == []

def test_user_memory_keeps_verbatim_source_provenance(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    source_id = store.add(AgentEvent(
        event_type="user_message",
        content="Meu nome é Otávio. Gosto de baixo elétrico.",
        metadata={"session_id": "session-1"},
    ))

    record = store.add_user_memory(source_id, "Gosto de baixo elétrico.")

    assert record.source_event_id == source_id
    assert record.source_event_type == "user_message"
    assert record.session_id == "session-1"
    assert record.content == "Gosto de baixo elétrico."
    assert record.created_at is not None
    assert store.list_user_memories() == [record]


def test_user_memory_rejects_assistant_and_initiative_sources(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    assistant_id = store.add(AgentEvent(
        event_type="assistant_message", content="Seu nome é Otávio."
    ))
    initiative_id = store.add(AgentEvent(
        event_type="initiative_result", content="O usuário se chama Otávio."
    ))

    with pytest.raises(ValueError, match="user_message"):
        store.add_user_memory(assistant_id, "Seu nome é Otávio.")
    with pytest.raises(ValueError, match="user_message"):
        store.add_user_memory(initiative_id, "O usuário se chama Otávio.")


def test_user_memory_rejects_claims_not_present_verbatim_in_source(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    source_id = store.add(AgentEvent(
        event_type="user_message", content="Gosto de baixo elétrico."
    ))

    with pytest.raises(ValueError, match="verbatim"):
        store.add_user_memory(source_id, "Gosto de baixo elétrico e guitarra.")


def test_user_memory_add_is_idempotent_and_list_is_chronological(tmp_path):
    store = EventStore(tmp_path / "test.sqlite3")
    first_id = store.add(AgentEvent(event_type="user_message", content="Minha gata se chama Alicia."))
    second_id = store.add(AgentEvent(event_type="user_message", content="Moro em Santo André."))

    first = store.add_user_memory(first_id, "Minha gata se chama Alicia.")
    duplicate = store.add_user_memory(first_id, "Minha gata se chama Alicia.")
    second = store.add_user_memory(second_id, "Moro em Santo André.")

    assert duplicate.id == first.id
    assert store.list_user_memories() == [first, second]
    assert store.list_user_memories(limit=1) == [first]


def test_user_memory_schema_migration_preserves_existing_events(tmp_path):
    import sqlite3

    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO events (timestamp, event_type, content, metadata_json) "
            "VALUES (?, ?, ?, ?)",
            ("2026-10-01T12:00:00+00:00", "user_message", "Moro em Santo André.", "{}"),
        )

    store = EventStore(path)
    assert store.recent()[0].content == "Moro em Santo André."
    record = store.add_user_memory(1, "Moro em Santo André.")

    assert record.source_event_id == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM user_memories").fetchone()[0] == 1
