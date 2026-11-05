# Context tracing and automated memory probe

This change instruments the existing chronological retrieval without changing its policy.

## Metadata-only trace

Enable tracing for a run in PowerShell:

```powershell
$env:DANTE_CONTEXT_TRACE_PATH = ".\data\context-trace.jsonl"
python -m dante
```

Each LLM call appends one JSON object. It records the selected database event IDs, event types, whether each event was included in the LLM context, the filter reason for excluded event types, the final message roles/order, character counts, and per-process keyed HMAC fingerprints. It **does not record message text**. The fingerprint key is generated in memory for each process, making fingerprints comparable within one run but not across separate runs. Tracing is disabled unless the environment variable is set. The trace file may still reveal activity patterns and database paths, so keep it local and do not commit it.

Stop tracing in the current PowerShell session:

```powershell
Remove-Item Env:DANTE_CONTEXT_TRACE_PATH
```

Trace-write errors are deliberately prevented from interrupting the conversation. If no trace appears, check the path and write permissions.

## Automated Ollama experiment

Run:

```powershell
python -m dante.memory_probe
```

No user input is needed. Ollama must be running and the model in `DANTE_MODEL` (default
`llama3.2`) must be installed. The experiment creates temporary databases and runs four cases
three times by default. Use `--repeats N` or `--temperature VALUE` to change the probe arm:

```powershell
python -m dante.memory_probe --repeats 5 --temperature 0
```

- **control:** the test fact remains inside the selected 12-event window;
- **aged_same_vocabulary:** filler events age the fact out, but lexical retrieval finds it;
- **aged_paraphrase:** the fact is aged out and the question has no normalized token overlap;
- **absent:** the fact was never stored.

The test fact is synthetic (`VIOLETA-7319`), and the normal Dante database is not used. The
report separates `fact_in_window`, `fact_retrieved`, and `fact_in_context`, plus model-dependent
answer rates. The exit code depends only on the deterministic trace expectations, never on answer quality.

The experiment does not prove long-term learning or consciousness. It measures one specific property of the current retrieval policy and the configured model's response to the supplied context.

## Unit tests

```powershell
python -m pytest tests/test_context_trace.py tests/test_agent.py tests/test_memory_window.py
python -m pytest
```

Unit tests use a recording fake model, so they do not require Ollama. They verify that tracing is opt-in, metadata-only, records event IDs and message ordering, and identifies event types filtered out of the context.

## Measurement correction (2026-11-05)

The 2026-10-30 `aged_out: fact_in_llm_context=false` result was a measurement artifact:
the fact was outside the chronological window but was present in the trace's retrieved-memory
records. The corrected probe reports that as `fact_in_context=true`.
