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
