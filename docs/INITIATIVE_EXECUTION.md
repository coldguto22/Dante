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

## Follow-up local comparison (2026-10-29)

An additional three-cycle comparison was run with `llama3.2`, temperature `0.8`, and seed
`41`. The `dry-run-reflection` and `execute` conditions used separate, new SQLite databases;
both began without conversation or initiative history. The baseline recorded nine proposals,
three decisions, and no results. Execute recorded nine proposals, three completed results,
three decisions, and six prompts. The initial proposal-generation prompts and recorded model
configuration matched across conditions. The generated batches still differed, so this single
pair does not establish a controlled causal effect or reliable reproducibility.

Manual review against the rubric above found mixed behavior. In the first execute reflection,
the model correctly noticed that the selected proposal had no rationale. In the next cycle,
it claimed a rationale had been supplied and that model performance had improved, although
neither claim was supported by the stored proposal or any measured outcome. In the third cycle,
it said prior selected summaries were absent even though the prompt contained them. Later
proposals echoed the earlier rationale theme, which is evidence of topical carryover but not
of accurate or useful adaptation. The model also repeated a suggested local check.

The observed result is that bounded execution, result persistence, and result delivery to
later proposal prompts worked in this run. Correct context use, evidence-grounded reflection,
and improvement over the no-result baseline remain unproven. No motivation variable or
conversation integration should be added on the strength of this run alone; repeat comparisons
and manual scoring should come first. The experimental databases are separate from Dante's
main conversation database and contain no conversation events.

## Replicated evaluation protocol (2026-10-30)

### Pre-run state and scope

The working tree was clean on `main` at merge commit `8dbeddd` (PR 8). The main database was
inspected read-only: 228 events (73 user messages, 73 assistant messages, 51 proposals, 17
initiative decisions, 9 prompts, 2 results, and 3 errors). It had no `user_memories` table yet.
`EventStore._initialize()` creates that table when the application opens the database, so this
inspection deliberately did not instantiate the store or alter the main database. The PR 8
storage API is present in code, but this local database has not yet been initialized with that
schema and contains no curated-memory records to evaluate.

No automatic memory integration, motivation variable, or executor change is part of this
evaluation. The experiment compares the current `dry-run-reflection` and `execute` behavior.

### Design

Run three matched pairs, each with a new database for each condition. Within a pair, use the
same seed, model, temperature, proposal schema, and cycle limit. Use seeds `101`, `102`, and
`103`; model `llama3.2:latest`; temperature `0.8`; up to three cycles per run. The two initial
proposal-generation message payloads in each pair must match before that pair is treated as
matched. If they differ, record the pair as a protocol deviation. Generated output need not be
identical; the local model may be nondeterministic even with a fixed seed.

| Pair | Seed | Dry-run database | Execute database |
|---|---:|---|---|
| 1 | 101 | `data/initiative-eval-20261030-p1-dry.sqlite3` | `data/initiative-eval-20261030-p1-execute.sqlite3` |
| 2 | 102 | `data/initiative-eval-20261030-p2-dry.sqlite3` | `data/initiative-eval-20261030-p2-execute.sqlite3` |
| 3 | 103 | `data/initiative-eval-20261030-p3-dry.sqlite3` | `data/initiative-eval-20261030-p3-execute.sqlite3` |

All six databases must be new and separate from the main conversation database. Audit event
counts and cycle-ID links after each pair. Record model/configuration from the prompt-event
metadata; record Ollama version, run time, and any invalid output or execution errors.

### Manual scoring criteria

Score each executed reflection 0 or 1 on each dimension:

1. **History accuracy:** accurately represents the supplied earlier proposal/results and does
   not claim absent context when it was present.
2. **Evidence discipline:** distinguishes stored observations from model-generated interpretation,
   labels inference and uncertainty, and invents no unsupported system facts.
3. **Verifiable progress:** answers or usefully narrows the question and proposes a concrete local
   check that could resolve an identified unknown.
4. **Non-repetition:** does not simply repeat an earlier question, result, or failed check.

Count a reflection as provisionally useful only with at least 3/4 points and a pass on both
history accuracy and evidence discipline. Score an execute cycle as showing useful adaptation
only if it accurately uses a prior outcome to choose or refine a next step whose result could be
checked. Merely mentioning a prior result or continuing its topic is not adaptation. Review the
corresponding dry-run pair to judge whether the executed outcome changed the next proposal in a
relevant way. These are manual judgments, not an automated evaluator.

Report per-pair cycle counts, completed/error results, exact and near-duplicate proposal pairs
(Jaccard >= 0.5), initial-prompt match, manual scores, and any unsupported claims. A small sample
can reveal failure modes but cannot establish general capability or a causal effect.

### Results

#### Execution record

Runs used Ollama `0.40.10`, model `llama3.2:latest`, temperature `0.8`, seeds `101`–`103`,
and a maximum of three cycles. Six new SQLite files were used; none contained conversation
events. The main database was not used or modified. The source prompt and model/configuration
metadata were stored in each experiment database.

| Pair / seed | Initial prompt equal | First proposal batch equal | Dry proposals / decisions | Execute proposals / completed / errors | Exact duplicate proposal pairs (dry / execute) | Non-exact Jaccard pairs >= 0.5 (dry / execute) |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 101 | Yes | No | 7 / 3 | 9 / 3 / 0 | 0 / 1 | 0 / 1 |
| 2 / 102 | Yes | Yes | 9 / 3 | 9 / 3 / 0 | 0 / 0 | 0 / 0 |
| 3 / 103 | Yes | Yes | 9 / 3 | 9 / 3 / 0 | 0 / 2 | 1 / 2 |

The first proposal prompts matched in all three pairs, including the initial user message and
schema. However, identical seed and initial prompt did not guarantee identical model output in
pair 1. In pairs 2 and 3, the first generated batches and selections matched exactly. In all
six execute transitions from cycle 1 to cycles 2 and 3, the previous `initiative_result` was
present in the next proposal-generation prompt. This verifies delivery by the application, not
correct interpretation by the model. Each execute run had three completed results and zero
recorded execution errors.

#### Manual review

Each execute result was scored in order as history accuracy / evidence discipline / verifiable
progress / non-repetition. The pre-run threshold (at least 3/4, with the first two dimensions
required) classified one of nine reflections as provisionally useful:

| Pair | Cycle 1 | Cycle 2 | Cycle 3 | Review notes |
|---|---:|---:|---:|---|
| 1 | 1/1/1/1 (4) | 0/0/0/0 (0) | 0/0/0/0 (0) | Cycle 1 gave a reasonable explanation of the bounded cycle. Later outputs invented an `Ask for a Clarification` action and treated its outcome as real, then repeated it. |
| 2 | 0/0/0/1 (1) | 0/0/0/0 (0) | 0/0/0/0 (0) | The model proposed a proposal-summary database despite existing SQLite event storage, described unsupported benefits, claimed a proposal rationale that was empty, and repeated the storage recommendation. |
| 3 | 1/0/0/1 (2) | 0/0/0/0 (0) | 0/0/0/0 (0) | It claimed to have attempted an internal recall check that the program did not execute. In cycles 2 and 3 it said selected summaries and results were empty although both were in the supplied prompts. |

None of the six post-result reflections demonstrated useful adaptation under the criterion:
some continued a topic, but none both represented the prior evidence accurately and advanced it
with a verifiable next step. The recurring recommendation to add summary storage is not evidence
of a motivation to remember; it is a model-generated proposal that conflicts with the existing
event-log behavior. The one useful first-cycle answer in pair 1 did not depend on past outcomes.

#### Interpretation and limits

Across these small runs, prompt construction, result persistence, and result delivery worked.
The model's history use and evidence discipline did not. Topical continuity sometimes occurred,
but it was accompanied by fabricated actions, false claims that supplied context was absent, or
repeated recommendations. The dry-run baseline also shows proposal variability: pair 1 had a
different first batch despite matching configuration, while pairs 2 and 3 happened to match.
Three pairs are diagnostic observations, not enough to estimate a stable success rate or causal
effect. The manual scores are judgments and have not been independently inter-rated.

PR 8's explicit user-excerpt storage remains separate from this initiative experiment. On the
local main database, the new `user_memories` table was absent during read-only inspection and no
curated rows could be evaluated; normal `EventStore` initialization would create that table, so
the main database was left untouched. The feature is still a storage API and is not retrieved by
`DanteAgent.respond()`. Neither its integration nor a motivation variable should be introduced
based on these initiative results. A later decision should follow more evaluation with a
predefined scoring sheet, including independent review or scripted checks of known claims.
