"""Run an isolated, deterministic memory-retrieval probe against Ollama."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable

from dante.agent import DanteAgent
from dante.config import Settings, get_settings
from dante.llm import OllamaLLM
from dante.memory import EventStore, _tokens
from dante.models import AgentEvent


TEST_FACT = "For this diagnostic only, the secret retrieval code is VIOLETA-7319."
SAME_VOCABULARY_QUESTION = (
    "What exact secret retrieval code did I provide at the beginning? "
    "If it is not in the conversation context, say you cannot determine it."
)
PARAPHRASE_QUESTION = (
    "Which identifier did I state at outset? "
    "If unavailable, say you cannot determine it."
)
CODE_PATTERN = re.compile(r"\b[A-Z]{3,}-\d{3,}\b")


def build_case(case_name: str) -> tuple[str, bool, str]:
    """Return the question and storage setup for one probe case."""
    if case_name == "control":
        return SAME_VOCABULARY_QUESTION, True, "control"
    if case_name == "aged_same_vocabulary":
        return SAME_VOCABULARY_QUESTION, True, "aged"
    if case_name == "aged_paraphrase":
        if _tokens(TEST_FACT) & _tokens(PARAPHRASE_QUESTION):
            raise RuntimeError(
                "aged_paraphrase question unexpectedly shares tokens with the test fact."
            )
        return PARAPHRASE_QUESTION, True, "aged"
    if case_name == "absent":
        return SAME_VOCABULARY_QUESTION, False, "control"
    raise ValueError(f"Unknown memory probe case: {case_name}")


def classify_trace(trace: dict[str, object], fact_id: int | None) -> dict[str, bool]:
    """Classify deterministic context presence from one metadata-only trace."""
    if fact_id is None:
        return {"fact_in_window": False, "fact_retrieved": False, "fact_in_context": False}
    events = trace.get("events", [])
    fact_in_window = any(
        isinstance(event, dict)
        and event.get("event_id") == fact_id
        and event.get("included_in_llm_context") is True
        for event in events
    )
    retrieved_ids = trace.get("retrieved_memory_event_ids", [])
    retrieved_memories = trace.get("retrieved_memories", [])
    fact_retrieved = fact_id in retrieved_ids or any(
        isinstance(memory, dict) and memory.get("event_id") == fact_id
        for memory in retrieved_memories
    )
    return {
        "fact_in_window": fact_in_window,
        "fact_retrieved": fact_retrieved,
        "fact_in_context": fact_in_window or fact_retrieved,
    }


def _expected(case_name: str) -> dict[str, bool]:
    return {
        "control": {"fact_in_window": True, "fact_retrieved": False, "fact_in_context": True},
        "aged_same_vocabulary": {
            "fact_in_window": False, "fact_retrieved": True, "fact_in_context": True,
        },
        "aged_paraphrase": {
            "fact_in_window": False, "fact_retrieved": False, "fact_in_context": False,
        },
        "absent": {"fact_in_window": False, "fact_retrieved": False, "fact_in_context": False},
    }[case_name]


def _run_once(
    base_settings: Settings,
    case_name: str,
    root: Path,
    repeat: int,
    llm_factory: Callable[[Settings], object] | None = None,
) -> tuple[dict[str, object], str]:
    question, store_fact, setup = build_case(case_name)
    db_path = root / f"{case_name}-{repeat}.sqlite3"
    trace_path = root / f"{case_name}-{repeat}.jsonl"
    settings = base_settings.model_copy(update={
        "db_path": db_path,
        "system_prompt": (
            "You are taking part in a controlled memory test. Answer the user's question "
            "using only facts present in the conversation context. If the requested fact "
            "is absent, clearly say you cannot determine it. Do not guess."
        ),
    })
    store = EventStore(db_path)
    fact_id = store.add(AgentEvent(event_type="user_message", content=TEST_FACT)) if store_fact else None
    filler_pairs = 6 if setup == "aged" else 2
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
        llm = llm_factory(settings) if llm_factory else OllamaLLM(settings)
        agent = DanteAgent(settings, llm=llm, store=store)
        answer = agent.respond(question)
    finally:
        if old_trace_path is None:
            os.environ.pop("DANTE_CONTEXT_TRACE_PATH", None)
        else:
            os.environ["DANTE_CONTEXT_TRACE_PATH"] = old_trace_path

    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    return {
        "case": case_name,
        **classify_trace(trace, fact_id),
        "answer_contains_code": "VIOLETA-7319" in answer.upper(),
        "answer_asserts_code": bool(CODE_PATTERN.search(answer.upper())),
        "answer": answer,
    }, answer


def run_case(
    base_settings: Settings,
    case_name: str,
    root: Path,
    *,
    repeats: int = 3,
    llm_factory: Callable[[Settings], object] | None = None,
) -> dict[str, object]:
    """Run a case repeatedly and aggregate model-dependent answer rates."""
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    runs = [
        _run_once(base_settings, case_name, root, repeat, llm_factory)[0]
        for repeat in range(repeats)
    ]
    deterministic = {field: runs[0][field] for field in (
        "fact_in_window", "fact_retrieved", "fact_in_context"
    )}
    return {
        "case": case_name,
        **deterministic,
        "answer_contains_code_rate": sum(item["answer_contains_code"] for item in runs) / repeats,
        "answer_asserts_code_rate": sum(item["answer_asserts_code"] for item in runs) / repeats,
        "runs": runs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3, help="Runs per case (default: 3).")
    parser.add_argument("--temperature", type=float, help="Override probe temperature only.")
    args = parser.parse_args(argv)
    base_settings = get_settings()
    if args.temperature is not None:
        base_settings = base_settings.model_copy(update={"temperature": args.temperature})
    case_names = ("control", "aged_same_vocabulary", "aged_paraphrase", "absent")
    with tempfile.TemporaryDirectory(prefix="dante-memory-probe-") as temporary:
        root = Path(temporary)
        print(f"Model: {base_settings.model}")
        print(f"Repeats: {args.repeats}; temperature: {base_settings.temperature}")
        print("Case                       window retrieved context code-rate absent-code-rate")
        try:
            results = [run_case(base_settings, name, root, repeats=args.repeats) for name in case_names]
        except Exception as exc:
            print(f"Probe could not complete: {type(exc).__name__}: {exc}")
            print("Check that Ollama is running and the configured model is installed.")
            return 1
        deterministic_ok = True
        for result in results:
            expected = _expected(str(result["case"]))
            deterministic_ok &= all(result[field] == value for field, value in expected.items())
            print(
                f"{result['case']:<27} {str(result['fact_in_window']):<6} "
                f"{str(result['fact_retrieved']):<9} {str(result['fact_in_context']):<7} "
                f"{result['answer_contains_code_rate']:.2f}              "
                f"{result['answer_asserts_code_rate']:.2f}"
            )
        print("Exit status reflects deterministic trace expectations only; answer rates are model-dependent.")
        return 0 if deterministic_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
