import json

from dante.config import Settings
from dante.memory import _tokens
from dante.memory_probe import (
    PARAPHRASE_QUESTION,
    TEST_FACT,
    build_case,
    classify_trace,
    run_case,
)


class RecordingChatLLM:
    def __init__(self, answer="I cannot determine it."):
        self.answer = answer

    def chat(self, messages):
        return self.answer


def test_probe_paraphrase_has_no_normalized_token_overlap():
    assert _tokens(TEST_FACT).isdisjoint(_tokens(PARAPHRASE_QUESTION))
    question, store_fact, setup = build_case("aged_paraphrase")
    assert question == PARAPHRASE_QUESTION
    assert store_fact is True
    assert setup == "aged"


def test_classify_trace_counts_retrieved_fact_as_context():
    trace = {
        "events": [{"event_id": 7, "included_in_llm_context": False}],
        "retrieved_memory_event_ids": [7],
        "retrieved_memories": [{"event_id": 7}],
    }
    assert classify_trace(trace, 7) == {
        "fact_in_window": False,
        "fact_retrieved": True,
        "fact_in_context": True,
    }


def test_probe_cases_report_deterministic_fields(tmp_path):
    settings = Settings(db_path=tmp_path / "unused.sqlite3")

    def factory(_settings):
        return RecordingChatLLM()

    expected = {
        "control": (True, False, True),
        "aged_same_vocabulary": (False, True, True),
        "aged_paraphrase": (False, False, False),
        "absent": (False, False, False),
    }
    for case_name, fields in expected.items():
        result = run_case(settings, case_name, tmp_path, repeats=1, llm_factory=factory)
        assert tuple(result[field] for field in (
            "fact_in_window", "fact_retrieved", "fact_in_context"
        )) == fields
