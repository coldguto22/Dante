"""Run an automated, isolated memory-retrieval probe against the configured Ollama model.

Usage: python -m dante.memory_probe

This experiment uses temporary databases and never reads or writes Dante's normal history.
It requires Ollama to be running and the configured model to be installed.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile

from dante.config import get_settings
from dante.agent import DanteAgent
from dante.llm import OllamaLLM
from dante.memory import EventStore
from dante.models import AgentEvent

TEST_FACT = "For this diagnostic only, the secret retrieval code is VIOLETA-7319."


def _run_case(base_settings, aged_out: bool, root: Path) -> dict[str, object]:
    case_name = "aged_out" if aged_out else "control"
    db_path = root / f"{case_name}.sqlite3"
    trace_path = root / f"{case_name}.jsonl"
    settings = base_settings.model_copy(update={
        "db_path": db_path,
        "system_prompt": (
            "You are taking part in a controlled memory test. Answer the user's question "
            "using only facts present in the conversation context. If the requested fact "
            "is absent, clearly say you cannot determine it. Do not guess."
        ),
    })
    store = EventStore(db_path)
    fact_id = store.add(AgentEvent(event_type="user_message", content=TEST_FACT))

    filler_pairs = 6 if aged_out else 2
    for index in range(filler_pairs):
        store.add(AgentEvent(
            event_type="user_message",
            content=f"Diagnostic filler question {index + 1}: discuss a neutral topic.",
        ))
        store.add(AgentEvent(
            event_type="assistant_message",
            content=f"Diagnostic filler response {index + 1}: neutral response.",
        ))

    old_trace_path = os.environ.get("DANTE_CONTEXT_TRACE_PATH")
    os.environ["DANTE_CONTEXT_TRACE_PATH"] = str(trace_path)
    try:
        agent = DanteAgent(settings, llm=OllamaLLM(settings), store=store)
        answer = agent.respond(
            "What exact secret retrieval code did I provide at the beginning? "
            "If it is not in the conversation context, say you cannot determine it."
        )
    finally:
        if old_trace_path is None:
            os.environ.pop("DANTE_CONTEXT_TRACE_PATH", None)
        else:
            os.environ["DANTE_CONTEXT_TRACE_PATH"] = old_trace_path

    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    fact_fingerprint = hashlib.sha256(TEST_FACT.encode("utf-8")).hexdigest()
    fact_in_context = any(
        event["event_id"] == fact_id
        and event["included_in_llm_context"]
        and event["content"]["sha256"] == fact_fingerprint
        for event in trace["events"]
    )
    return {
        "case": case_name,
        "fact_in_llm_context": fact_in_context,
        "answer_contains_code": "VIOLETA-7319" in answer.upper(),
        "answer": answer,
    }


def main() -> int:
    base_settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="dante-memory-probe-") as temporary:
        root = Path(temporary)
        print(f"Model: {base_settings.model}")
        print("Using isolated temporary SQLite databases; normal Dante history is untouched.")
        try:
            control = _run_case(base_settings, aged_out=False, root=root)
            aged_out = _run_case(base_settings, aged_out=True, root=root)
        except Exception as exc:
            print(f"Probe could not complete: {type(exc).__name__}: {exc}")
            print("Check that Ollama is running and the configured model is installed.")
            return 1

        print(json.dumps({"control": control, "aged_out": aged_out}, ensure_ascii=False, indent=2))
        print(
            "Interpretation: the control should include the fact; the aged-out case should not. "
            "The answer comparison is model-dependent and is evidence about this run only."
        )
        return 0 if control["fact_in_llm_context"] and not aged_out["fact_in_llm_context"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
