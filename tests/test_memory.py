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
