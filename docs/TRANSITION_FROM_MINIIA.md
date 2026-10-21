# Transition from MiniIA to Dante

**Status:** Working architectural decision record  
**Date:** 2026-10-21  
**Scope:** Documentation and research direction only. This document does not imply that proposed mechanisms have been implemented.

This document explains how the new Dante repository relates to the earlier MiniIA experiments. It records what is worth preserving, what should be redesigned, what is intentionally deferred, and how future changes should be evaluated. It complements [Foundations and Initial Decisions](FOUNDATIONS.md); it does not replace it.

## 1. Executive decision

MiniIA should remain a historical research lab and source of lessons, not a codebase to migrate wholesale. Dante should continue from its smaller baseline and adopt a mechanism only when its purpose, behavior, limits, and evaluation criteria are explicit.

The immediate priority is **not adding more features**. It is establishing a clear transition record and a testable plan. Further implementation should wait until the baseline is understood and the next workshop materials have been reviewed.

Distinguish throughout the project:

- **Idea worth preserving:** a research question or design principle that remains valuable.
- **Mechanism worth reimplementing:** a concrete behavior whose implementation can be isolated and tested.
- **Legacy implementation:** existing code that may contain useful experiments but is not presumed correct or necessary.
- **Implemented capability:** behavior demonstrably present in the current code and verified at an appropriate level.
- **Observed behavior:** output seen in a particular run, which may not generalize.
- **Hypothesis:** a claim that still needs a controlled test.

## 2. Why a new repository?

MiniIA accumulated experiments involving local language models, OCR, autonomous research, internal-state variables, diaries, semantic retrieval, consolidation, and alternative model arrangements. These experiments are valuable because they expose questions and failure modes. However, the older code also mixes legacy entry points, compatibility layers, heuristics, and mechanisms that are difficult to evaluate independently.

Dante starts smaller so that its behavior can be reconstructed from explicit inputs, state, decisions, actions, and outcomes. This is not a judgment that every MiniIA mechanism failed. It is a decision not to carry implementation complexity forward without evidence that it serves the new research goals.

### 2.1 Design principles for the transition

1. Preserve research questions and useful lessons, not code merely because it already exists.
2. Reimplement mechanisms in small, independently testable steps.
3. Keep the model's generated explanation separate from the program's actual decision process.
4. Do not interpret a fluent self-description as evidence that an internal state caused a decision.
5. Make behavior, configuration, errors, and outcomes observable.
6. Prefer reversible experiments and explicit permission boundaries.
7. Do not silently discard useful history; document what is retained, transformed, or removed when memory policies change.
8. Keep the architecture provisional while new workshop material may change the engineering options.

## 3. MiniIA mechanism review

This review is based on the inspected repository and its implementation patterns. It is a design assessment, not a claim that every historical behavior has been reproduced or exhaustively tested.

| Area in MiniIA | Lesson worth preserving | Decision for Dante |
|---|---|---|
| PHILOSOPHY.md and foundational principles | Explicitly articulate the kind of agent being explored, including non-compulsory interaction and the possibility of silence. | Preserve the principles as research commitments and revisit them critically. Do not rely on a long philosophical prompt as a substitute for mechanisms. |
| Homeostasis and valence (dante/core/homeostasis.py, dante/core/valence.py) | Internal variables may influence action selection and resource-sensitive behavior. | Reintroduce one variable at a time with an operational definition, update rule, trace, and test. Values are engineering abstractions, not proof of felt states. |
| Curiosity (dante/cognition/curiosity.py) | Unresolved questions and novelty can be candidate priorities. | Define uncertainty, novelty, progress, and repetition. Test whether these measures change useful choices rather than simply producing more activity. |
| Self-model (dante/core/self_model.py) | A record of recurring topics, preferences, aversions, and goals could help continuity. | Do not treat keyword associations as reliable discoveries of identity. Separate observations, inferred patterns, and tentative hypotheses; retain provenance and allow correction. |
| Diary and consolidation (dante/memory/diary.py, dante/memory/consolidation.py) | Summaries may aid continuity; original events and contradictions should remain inspectable. | Begin with the event log and straightforward retrieval. Add summaries only with traceability to source events. Treat contradiction detection as fallible. |
| Silence / cycle suppression (dante/cognition/silence.py) | Not acting can be a legitimate choice; repetitive cycles should be detectable. | If a decision loop is introduced, record why it chose not to act and evaluate whether silence avoided waste or missed useful work. |
| Asas autonomous research (asas.py, dante/action/asas.py) | Research can be a candidate activity selected by the agent rather than only a direct user request. | Preserve the goal, redesign activation and result evaluation, and introduce only after capability boundaries and decision logging exist. |
| Screen perception and OCR (dante/perception/screen.py, dante/perception/ocr.py) | The agent may eventually use visible computer context when relevant. | Keep on the roadmap, not in the initial baseline. Start with explicit on-demand capture; later evaluate controlled periodic observation and only then agent-selected observation. |
| Two-model / System 1 and System 2 arrangement | Different model sizes may have different cost and quality trade-offs. | Defer until a benchmark shows that model separation improves a defined task enough to justify latency and complexity. |
| Mamba experiment and context continuation | Recurrent-state ideas may be worth investigating. | Do not describe context continuation as a true exposed recurrent Mamba state. Keep it out of the core until a specific need emerges. |
| ChromaDB / embeddings / semantic retrieval | Semantic retrieval may help when event history grows beyond simple retrieval. | Defer until tests show that chronological SQLite retrieval is inadequate for a defined use case. |
| Legacy wrappers and multiple entry points | Compatibility can preserve access to older experiments. | Avoid importing old wrappers or parallel loops into the new core. Keep one clear execution path wherever possible. |

## 4. Current Dante baseline: what it does and does not establish

At the time of this record, the new repository contains a small Python conversational prototype with Ollama integration, Pydantic models, a SQLite event store, and tests using a fake language-model client.

### 4.1 Implemented at baseline

- A terminal conversation loop with an explicit exit command.
- An Ollama-backed chat adapter.
- Pydantic data models, including a structured ActivityProposal schema.
- SQLite persistence for timestamped events.
- Retrieval of a limited number of recent events to construct conversational context.
- Unit tests for model validation, memory operations, and agent behavior using a fake LLM.

The existing ActivityProposal schema is not yet an autonomous decision system. Its existence does not mean the agent currently evaluates proposals or executes their requested actions.

### 4.2 Not yet implemented as an autonomous capability

- An independent initiative loop that can run without a new user message.
- A capability registry describing which tools are actually available.
- A policy that selects among proposals using explicit state, cost, relevance, uncertainty, and prior outcomes.
- Structured profile memory that reliably distinguishes a person's primary name from an alternate form of address.
- An outcome-based learning or adaptation mechanism.
- Autonomous web research, OCR-based perception, or unrestricted external action execution.
- Evidence that homeostatic variables influence behavior.
- Evidence of subjective consciousness.

A successful unit-test suite establishes that tested code paths meet those tests. Tests with a fake LLM do not establish real Ollama connectivity, model reliability, research quality, or autonomy. A particular conversation can reveal a useful failure mode but is not, by itself, a systematic evaluation.

### 4.3 Early observations to turn into tests

Initial conversations exposed several issues:

1. **Unsupported research implication:** Dante answered a question about consciousness with generic knowledge and reflective language, without performing web research. It should not imply that sources were checked when they were not.
2. **Capability overstatement/understatement:** Dante correctly said it lacked browsing in that run, but also denied abilities such as inference too broadly. The system needs an explicit registry of available tools and a distinction between model reasoning, implemented tools, and unverified claims.
3. **Fact conflation:** When asked for the user's name after a restart, Dante combined the primary name and alternate form of address. This is a memory representation and retrieval problem; more conversational history alone may not solve it.
4. **Mirroring of framing:** When asked about becoming an independent agent with a thirst for knowledge, Dante described enthusiasm and desire. Such language may reflect the user's framing or model behavior; it is not evidence of persistent intrinsic motivation.

These observations motivate tests. They should not be generalized to all runs or models without further evidence.

## 5. Capability boundaries and memory: candidate improvements

When coding resumes, two small supporting mechanisms are candidates for early implementation. Their design should be finalized after the next workshop materials are reviewed.

### 5.1 Capability registry

The program should maintain an explicit list of capabilities, each with a status such as:

- **Available:** implemented and callable in the current configuration.
- **Unavailable:** not implemented, disabled, or missing a dependency.
- **Planned:** a future direction, not callable now.
- **Restricted:** implemented but requires specific authorization or constraints.

The registry should distinguish the model's general ability to generate or reason about text from tools the application can actually execute. Responses about capabilities should be grounded in this registry. If a capability has not been evaluated, the system should state that uncertainty rather than confidently claiming either success or impossibility.

### 5.2 Structured profile memory

Store user-provided facts in typed records with a source and timestamp where appropriate. For example, a primary name and an optional alternate form of address should be separate fields, not concatenated into one value. Inferred preferences should be labeled as inferences and must not silently overwrite explicit statements.

This differs from event history: the event log records what happened, while profile memory offers a controlled representation of facts that may be useful later. The design should preserve provenance and support correction.

Neither mechanism alone creates autonomy. They make the system's claims and context more reliable, a prerequisite for evaluating later decisions.

## 6. Asas: research as an action, not a magic ability

The old research pathway appears to be gated by several conditions: a feature flag, a curiosity threshold, and a minimum number of cycles since the previous search. These gates may explain why it activated rarely, but the contribution of each condition should be measured before attributing behavior to one cause.

The old search adapter retrieves results such as titles, URLs, and snippets. Retrieval of snippets is not the same as opening sources, validating claims, assessing source quality, or deciding whether evidence changes a hypothesis.

A future research flow should be separable into:

1. Formulate a question and explain its relevance.
2. Evaluate whether research is warranted under the current policy and resource limits.
3. Execute a bounded search through an explicitly registered tool.
4. Record the query, result metadata, source URLs, timestamp, and errors.
5. Evaluate returned evidence and identify what remains uncertain.
6. Decide whether to update a hypothesis, ask a narrower question, stop, or report insufficient evidence.

Initially, research should be invoked deliberately and logged. Autonomous initiation should be tested later, once proposal selection and permissions can be inspected. Dante must not imply it searched or verified information when it did not.

## 7. OCR and screen perception: staged roadmap

OCR should not be added merely because MiniIA already has it. Screen content can contain private or sensitive information, and extracted text is only a partial representation of what is visible.

A staged path is preferred:

- **Stage A — on-demand:** the user explicitly requests a capture; show what is being captured and allow the operation to be stopped.
- **Stage B — controlled observation:** if justified, introduce a visible, configurable schedule with deduplication, limited retention, and clear pause/stop controls.
- **Stage C — agent-proposed observation:** only after the decision policy exists, allow Dante to propose observing the screen for a stated purpose. The proposal must still pass the permission policy.

Screen observation should be off by default. Each stage requires tests for duplicate text, capture errors, resource cost, retention, and user control. OCR must not be described as complete visual understanding.

## 8. Relationship to the professor's workshop

The first workshop notebook inspected so far demonstrates engineering techniques including local Llama/Ollama use, structured output with Pydantic, extraction of article text with Trafilatura, and predefined task/agent orchestration with CrewAI. It includes exercises involving news analysis, scientific-paper comparison, and structured classification.

These techniques may be useful, but they solve different problems:

- **Structured output** can make proposals easier to validate; it does not make a proposal true or useful.
- **Article extraction** can supply source text to analyze; it does not itself establish source quality.
- **Predefined CrewAI tasks** can orchestrate a known workflow; Dante's central research question is how one agent might propose and select its own next activity under constraints.
- **RAG, MCP, multi-agent orchestration, and CUDA** should be adopted only when later materials and experiments identify a concrete need.

This section is provisional. The next workshop session and its Jupyter notebook may add, refine, or overturn these engineering choices. New content should be recorded as source-derived technique, architectural inference, or an open question—not silently merged into the design.

## 9. Evaluation rules before adding complexity

Every new mechanism should answer five questions before implementation:

1. **Purpose:** which specific observed limitation or research question does it address?
2. **Mechanism:** what input does it use, and what behavior should it change?
3. **Measurement:** what observable result would count as improvement or failure?
4. **Control:** what are its limits, failure behavior, and stop conditions?
5. **Removal criterion:** what evidence would justify revising or removing it?

Where practical, compare a baseline with a modified version while keeping other conditions stable. Record the model and version, prompt/configuration, relevant state, proposals, selected action, execution result, errors, and outcome. Do not use eloquence, action count, or self-reported motivation as the sole success measure.

### Candidate evaluation targets

| Dimension | Example of an observable test |
|---|---|
| Capability accuracy | Ask about implemented and planned tools; verify that claims match the registry. |
| Fact retrieval | Ask for a primary fact and a distinct alternate form; verify that they are not conflated. |
| Initiative | In a controlled no-new-user-input interval, measure whether proposed activities are relevant and permitted. |
| State sensitivity | Change one internal variable and test whether the selected action changes in the predicted direction. |
| Research quality | Verify that each factual research claim can be traced to retrieved source evidence, or is marked unverified. |
| Continuity | Restart the process and test whether relevant state is retrieved accurately. |
| Silence and repetition | Check whether the system can decline an unhelpful action and avoid repeating failed or redundant work. |
| Traceability | Reconstruct a decision from recorded inputs, state, policy, and outcome. |

These are candidate tests, not a claim that all evaluation infrastructure already exists.

## 10. Provisional implementation sequence

This order is intentionally conservative and may be revised after the workshop.

1. **Document the transition** between MiniIA and Dante and keep the research hypotheses explicit.
2. **Review workshop material** from the next session and add relevant findings with provenance.
3. **Capability registry** so claims about tools reflect the actual runtime.
4. **Structured profile memory** to separate explicit facts, inferences, and event history.
5. **Auditable proposal-selection policy**, initially operating in a logging or dry-run mode.
6. **A bounded initiative cycle** only after proposals, state, selection, and stop conditions are testable.
7. **One tool at a time**, likely research before OCR if evaluation supports that choice.
8. **Motivation variables and outcome-based adaptation**, introduced individually with controlled tests.
9. **More complex retrieval, multiple models, or frameworks** only when measured limitations justify them.

Do not interpret this sequence as a promise to implement every item. A step can be postponed, redesigned, or rejected when evidence or workshop material warrants it.

## 11. Decisions and open questions

### Decisions recorded here

- Keep MiniIA as a historical experimental reference.
- Keep Dante's current baseline small and understandable.
- Do not migrate legacy modules wholesale.
- Preserve the ideas of initiative, internal-state modeling, continuity, research, and silence as hypotheses to investigate.
- Defer OCR, semantic databases, multi-model orchestration, Mamba-related experiments, and autonomous external actions until justified.
- Make capability claims, decisions, and research outcomes traceable.
- Keep the distinction between operational behavior and subjective consciousness explicit.
- Review the next workshop materials before expanding implementation.

### Open questions

- What did the next workshop add that changes the technical plan?
- Which model performs adequately on the available machine, and at what latency and resource cost?
- What is the smallest state representation that improves decisions?
- How should energy, saturation, curiosity, and goal tension be defined and measured?
- What level of research verification is appropriate for the first tool?
- When does chronological event retrieval become insufficient?
- What privacy and retention policy is needed before screen observation?
- Which observed behaviors would count as meaningful adaptation rather than prompt mirroring or post-hoc explanation?

## 12. Change policy for this document

This is a working decision record, not a fixed manifesto. Future edits should state what changed and why. New workshop material should be reflected with its source and should distinguish:

- what the notebook or lecture explicitly demonstrates;
- what is inferred for Dante's architecture;
- what remains a hypothesis or question;
- what has actually been implemented and tested.

Do not replace the existing Foundations document or repository README merely to duplicate this document. Update those files only when a specific, justified change to their purpose or content is needed.
