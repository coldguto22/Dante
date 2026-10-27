from dante.memory import EventStore
from dante.memory_audit import audit_database
from dante.models import AgentEvent


def test_audit_reports_recent_conversation_window_without_internal_events(tmp_path, capsys):
    path = tmp_path / "audit.sqlite3"
    store = EventStore(path)
    store.add(AgentEvent(event_type="user_message", content="Meu nome é Otávio"))
    store.add(AgentEvent(event_type="error", content="temporary test error"))
    store.add(AgentEvent(event_type="assistant_message", content="Olá"))

    status = audit_database(path, show_context=True)
    output = capsys.readouterr().out

    assert status == 0
    assert "Total events: 3" in output
    assert "Last 12 conversation messages" in output
    assert "eligible for LLM context" in output
    assert "[user] Meu nome é Otávio" in output
    assert "[assistant] Olá" in output
    assert "temporary test error" not in output


def test_audit_search_finds_older_event(tmp_path, capsys):
    path = tmp_path / "audit.sqlite3"
    store = EventStore(path)
    store.add(AgentEvent(event_type="user_message", content="Você pode me chamar de Guto"))

    status = audit_database(path, search="guto")
    output = capsys.readouterr().out

    assert status == 0
    assert "Search matches for 'guto': 1" in output
    assert "Você pode me chamar de Guto" in output


def test_audit_does_not_create_missing_database(tmp_path, capsys):
    path = tmp_path / "missing.sqlite3"

    status = audit_database(path)
    output = capsys.readouterr().out

    assert status == 1
    assert not path.exists()
    assert "database file does not exist" in output
