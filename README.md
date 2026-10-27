# Dante

Dante is an experimental research and engineering project exploring local AI agents that can select activities on their own initiative, maintain continuity between sessions, and adapt their behavior based on internal state and previous outcomes.

The project starts as a clean repository informed by experiments in [MiniIA](https://github.com/coldguto22/MiniIA). MiniIA is a historical reference, not an architecture that must be copied wholesale.

## Research questions

- Can an agent select useful activities without waiting for a new user message?
- Can explicitly modeled internal variables influence which activity it selects?
- Can it maintain goals, open questions, and useful memories across restarts?
- Can it evaluate the outcomes of its actions and use those observations in later decisions?
- How can these behaviors be measured without confusing fluent explanations with evidence of autonomy?
- Which aspects of consciousness can be investigated empirically, and which conclusions remain unsupported?

These are hypotheses and questions, not claims that Dante already has these capabilities. Behavioral autonomy does not establish subjective consciousness.

## Initial principles

1. **Start small.** Establish a reproducible baseline before adding complex mechanisms.
2. **Separate model and agent.** The language model proposes; ordinary program logic manages state, validates proposals, applies permissions, executes actions, and records outcomes.
3. **Measure before expanding.** Prefer experiments that can fail and produce interpretable results.
4. **Preserve traceability.** Record relevant state, decisions, actions, errors, and outcomes.
5. **Distinguish initiative from randomness.** Acting without a new prompt is not automatically useful autonomy.
6. **Bound actions explicitly.** Tool access and permissions must be defined outside the model's free-form text.
7. **Treat personality as a research question.** Do not hard-code a complete personality or a list of interests before there is evidence that they are useful.
8. **Avoid unsupported claims.** A system describing feelings, keeping a diary, or reflecting on itself is not by itself evidence of subjective experience.

## Current implementation

- A local interactive conversation baseline using Ollama.
- SQLite event history and lexical retrieval of older user-authored memories.
- A code-owned capability registry that distinguishes available, planned, restricted, and unavailable capabilities.
- A bounded initiative prototype that asks the local model for up to three structured proposals, authorizes them against the registry, selects one using a deterministic novelty baseline, and records the decision.
- The initiative prototype is dry-run only. It does not execute proposals or access web, arbitrary files, shell commands, or external services.

## Run locally

Install the project and development dependencies in the active virtual environment:

```powershell
python -m pip install -e ".[dev]"
```

Start the interactive conversation:

```powershell
python -m dante
```

Simulate one initiative cycle:

```powershell
python -m dante.initiative
```

Simulate up to three cycles:

```powershell
python -m dante.initiative --cycles 3
```

The initiative cycle uses the configured Ollama model and the same `DANTE_DB_PATH` SQLite database. It records candidates as `proposal` events and the selection as an `initiative_decision` event. To inspect recent records, use `python -m dante.memory_audit`.

Configuration is environment-based. Existing settings include `OLLAMA_HOST`, `DANTE_MODEL`, `DANTE_DB_PATH`, `DANTE_TEMPERATURE`, and optional `DANTE_SEED`. Ollama must be running and the configured model must be installed.

## Safety and evaluation scope

The registry is defined in code, not by the model. A proposal being authorized means only that it may be recorded and considered for selection in dry-run; it does not mean the action was performed. Execution mode is deliberately rejected until an explicit executor and permission model are designed.

The novelty policy is only an initial measurable baseline. It can favor novelty over usefulness, and lexical similarity is imperfect. Tests cover schema/registry authorization, rejection of external-action requests, bounded cycles, and event recording. Passing these tests would establish software behavior, not consciousness or general autonomy.

See [docs/FOUNDATIONS.md](docs/FOUNDATIONS.md) for the project's research framing and [docs/MEMORY_DIAGNOSTICS.md](docs/MEMORY_DIAGNOSTICS.md) for memory inspection.
