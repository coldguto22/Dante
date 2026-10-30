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
- An opt-in execution mode that runs only the selected `reflect` action through the configured local model, records its result or error, and supplies recent outcomes to later cycles. Other action types remain unexecuted.
- A further opt-in `--external-feedback` experiment for execute mode that reports deterministic citation/field checks to later cycles; it does not score usefulness or verify progress.
- The initiative prototype does not access web, arbitrary files, shell commands, or external services.

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

Run up to three cycles with bounded local reflection execution:

```powershell
$env:DANTE_DB_PATH = "data/initiative-experiment.sqlite3"
python -m dante.initiative --cycles 3 --mode execute
```

Use a separate database path for experiments so initiative events do not mix with the conversation history. The experiment still requires Ollama and the configured local model.

The initiative cycle uses the configured Ollama model and the `DANTE_DB_PATH` SQLite database. It records prompts/configuration as `initiative_prompt` events, candidates as `proposal` events, and the selection as an `initiative_decision` event. Execute mode additionally records `initiative_result` events for local reflections, including errors, and supplies recent results to subsequent proposals and reflections. To inspect recent records, use `python -m dante.memory_audit`.

Configuration is environment-based. Existing settings include `OLLAMA_HOST`, `DANTE_MODEL`, `DANTE_DB_PATH`, `DANTE_TEMPERATURE`, and optional `DANTE_SEED`. Ollama must be running and the configured model must be installed.

## Safety and evaluation scope

The registry is defined in code, not by the model. A proposal being authorized means it may be recorded and considered for selection; it does not itself mean the action was performed. Execute mode supports only local `reflect` actions through the configured model. Other action types are not executed; web, arbitrary file access, shell commands, and external services remain unavailable to the initiative loop.

The novelty policy is only an initial measurable baseline. It can favor novelty over usefulness, and lexical similarity is imperfect. Tests cover schema/registry authorization, rejection of external-action requests, bounded cycles, and event recording. Passing these tests would establish software behavior, not consciousness or general autonomy.

See [docs/FOUNDATIONS.md](docs/FOUNDATIONS.md) for the project's research framing, [docs/MEMORY_DIAGNOSTICS.md](docs/MEMORY_DIAGNOSTICS.md) for memory inspection, and [docs/INITIATIVE_EXECUTION.md](docs/INITIATIVE_EXECUTION.md) for the bounded execution experiment and evaluation procedure.
