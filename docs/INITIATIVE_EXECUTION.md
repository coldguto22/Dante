# Bounded initiative execution experiment

## What execute mode does

`python -m dante.initiative --mode execute` can execute only a selected `reflect` proposal. It sends the proposal, up to five recent selected summaries, and up to three recent execution outcomes to the configured local Ollama model. The result or error is stored as an `initiative_result` event linked to the cycle ID. Later cycles receive those results as historical model output, not as verified facts or instructions.

Other action types are not executed. Web access, arbitrary file access, shell commands, external writes, and additional retries are not part of this executor. A selected `stop` ends the loop without execution. The loop remains bounded to ten cycles.

## Reproducible local comparison

Use the same model and seed for both runs, and keep the two databases separate from the conversation database. `dry-run-reflection` uses the same restricted proposal schema as execute mode, but does not call the executor; this controls for the action set when comparing the effect of execution and outcome history.

```powershell
$env:DANTE_SEED = "41"
$env:DANTE_DB_PATH = "data/initiative-baseline-v2.sqlite3"
python -m dante.initiative --cycles 3 --mode dry-run-reflection

$env:DANTE_DB_PATH = "data/initiative-execution-v3.sqlite3"
python -m dante.initiative --cycles 3 --mode execute
```

Inspect each database with `python -m dante.memory_audit`. In the execution run, review `initiative_result` events and confirm each result has the same `cycle_id` as its decision. The CLI output prints completed reflection results. If Ollama is unavailable or the model is missing, the integration run cannot be considered complete; deterministic tests use a fake model and do not substitute for this check.

The event log stores each proposal and reflection prompt, model name, temperature, seed, proposals, decisions, results, and errors. Record the Ollama version with the run notes. Compare:

- exact and lexical near-duplicate proposals;
- actions completed and execution errors;
- whether the next cycle's proposal prompt contains the prior result;
- whether the model's next proposal meaningfully uses that result.

The last item requires reviewing actual model outputs. Presence of a result in the prompt proves only that the program supplied it, not that the model used it correctly. Three cycles are an initial integration probe, not evidence of general autonomy or consciousness.

## Automated test scope

The test suite uses deterministic fake LLM/executor components to verify authorization, bounded execution, result/error persistence, result propagation, and duplicate rejection within a proposal batch or against recent selections in reflection-only modes. These checks establish code-path behavior only. They do not evaluate Ollama response quality or whether reflection improves a later decision.

## Manual outcome rubric

For this experiment, a reflection is provisionally useful when it answers or narrows the selected question using the code-provided experiment context and supplied event history, distinguishes evidence from inference and unknowns, and proposes a concrete bounded next check when information is missing. A fluent response that only says more context is needed, repeats prior outcomes without applying them, or invents facts does not count as useful progress. Review each result manually; this prototype does not yet implement an outcome-quality evaluator.

## Pilot run (2026-10-28)

The local `llama3.2` model was run with seed `41` and temperature `0.8` for three cycles in each condition. The baseline used `dry-run-reflection`; execute mode used the same proposal schema in a separate SQLite database. Both runs generated nine proposals and selected three reflections. The baseline recorded three decisions and no results. Execute mode recorded three completed reflection results, three decisions, and six prompts (proposal-generation and reflection prompts for each cycle). All three cycle IDs had matching result and decision records. A read-only audit confirmed that neither experiment database contained conversation messages.

No exact duplicate proposal summaries appeared in either three-cycle run. A post-run pairwise Jaccard check over the nine proposals in each condition found no pairs at or above 0.5. The execute database's proposal-generation prompts contain the preceding cycle's result in cycles 2 and 3, which verifies that the program supplied outcomes to later decisions. However, the generated reflections were not consistently useful: cycle 2 claimed that recent summaries were missing even though the prompt included the prior selected summary, and suggested implementing history storage that already exists. Under the rubric above, execution and data propagation passed, while correct interpretation and useful adaptation remain unproven and this run contains a concrete failure. This is a small integration probe, not a controlled statistical result.
