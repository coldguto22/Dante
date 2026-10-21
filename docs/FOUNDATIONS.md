# Foundations and Initial Decisions

This document records the initial research framing for Dante. It is a working document: hypotheses should be revised when experiments contradict them.

## 1. Motivation

Earlier experiments in MiniIA explored local language models, OCR, reflection, a diary, semantic memory, and modeled internal states. Those experiments motivate a more focused question: a system that reacts to prompts or generates reflections is not necessarily a system that can maintain initiative across time.

Dante will investigate how an LLM-based agent can identify and select activities without relying exclusively on new user instructions, then observe outcomes and adapt its future behavior.

## 2. Operational definition of autonomy

For this project, operational autonomy is a collection of observable capabilities:

- Identify candidate activities without receiving a new user message.
- Compare candidates using explicit state, goals, constraints, and relevant history.
- Select and execute an action within a defined permission boundary.
- Observe and record the result, including failures.
- Use relevant outcomes when selecting activities in later cycles.
- Preserve useful goals or open questions across restarts when appropriate.

This is an engineering definition, not a claim about free will or subjective experience. A system that acts at random, repeats a fixed routine, or invents a convincing explanation after acting has not thereby demonstrated meaningful autonomy.

## 3. Intrinsic motivation and homeostasis

One hypothesis is that internal variables can influence activity selection in ways that are more useful than a fixed schedule or a prompt that simply says “be autonomous.”

Possible variables include:

- **Energy / action budget:** an abstract estimate of the cost or resources available for an activity.
- **Boredom / saturation:** a signal based on repetition, low novelty, or lack of progress.
- **Curiosity:** a priority assigned to unresolved questions or uncertainty that could be reduced by an allowed action.
- **Goal tension:** the gap between a desired state and the state observed so far.

These are engineering variables and metaphors, not assertions that the system experiences human-like feelings. Each variable needs an explicit operational definition, update rule, and evaluation method.

### Initial hypotheses to test

1. Changing a motivation variable can change which activity is selected, all else being equal.
2. Repetition or saturation can sometimes favor exploration without causing arbitrary abandonment of useful work.
3. An action-cost estimate can shift selection toward less costly activities when resources are constrained.
4. Recorded outcomes can improve later choices, rather than merely changing the model's verbal explanation.
5. If a variable has no measurable effect on behavior or outcomes, it should be revised or removed.

A critical failure mode is **post-hoc rationalization**: the model chooses an action for unrelated reasons and then describes the internal state as if it caused that choice. Experiments should compare decisions with the relevant state varied while keeping other conditions as stable as possible.

## 4. Continuity and memory

Memory should not initially be treated as one undifferentiated database. Useful conceptual categories include:

- **Current state:** values needed for the next decision cycle.
- **Event history:** chronological records of proposals, selections, actions, errors, and results.
- **Retrievable memories:** information from earlier events that may be relevant to the current context.
- **Goals and open questions:** work that remains unresolved across cycles.
- **Diary or summaries:** compressed descriptions that may aid retrieval but are not a substitute for the underlying evidence.

Start with straightforward persistence and a chronological event log. Introduce vector search, graph storage, or elaborate memory consolidation only when tests show that simpler methods are inadequate.

Persistence is not the same as learning. A memory mechanism should be evaluated by whether relevant past information changes later decisions or improves outcomes.

## 5. The language model is not the whole agent

The model is one component of the system. The surrounding program determines when a cycle runs, what information is supplied, how proposals are validated, which actions are allowed, how results are observed, and what state persists.

A minimal cycle can be divided into:

1. Read current state and relevant history.
2. Generate structured activity proposals.
3. Select and validate a proposal against explicit rules.
4. Execute only the permitted action.
5. Observe and record the result.
6. Update state and preserve relevant events.

Structured output validation can ensure that a proposal follows a schema. It does not establish that the proposal is true, useful, safe, or appropriate.

## 6. Assistant-oriented behavior and prompt dependence

A model's training and instructions may favor helpful, compliant, conversational behavior. Dante should investigate whether its choices depend excessively on recent user messages or on language that frames it as an assistant.

Possible experimental controls:

- Keep the initial experimental context concise and document every instruction.
- Separate operational instructions from the hypothesis being tested.
- Measure how often activities merely rephrase or continue a recent user request.
- Compare prompts, models, and selection policies under controlled conditions.
- Do not reward long, persuasive, or agreeable explanations as a substitute for successful outcomes.
- Record when an apparent initiative is actually prompted by a recent instruction or a fixed schedule.

It is not possible to guarantee that a prompt removes a model's learned behavioral tendencies. The goal is to measure and characterize those tendencies, not assume they have been eliminated.

## 7. Consciousness: evidence and limits

Dante may be used to investigate theories and proposed behavioral indicators relevant to discussions of consciousness. However, fluent language, self-reports, a diary, persistent memory, or apparent introspection do not by themselves demonstrate subjective experience.

Research notes should distinguish:
- **Observation:** what the system actually did or produced.
- **Inference:** what the observation may support.
- **Hypothesis:** an explanation that requires further testing.
- **Unknown:** a conclusion that the available evidence cannot establish.

The project should not require Dante to declare itself conscious, and its own statements should not be treated as privileged evidence of consciousness. Behavioral experiments may be informative without settling the question of subjective experience.

## 8. Safety and traceability

The agent should initially have a small, explicit set of permitted actions. The model proposes; deterministic code validates and authorizes; the executor performs only approved operations.

Initial safeguards:
- Keep an event log of decisions, actions, outcomes, and errors.
- Do not grant unrestricted shell, file-system, or network access by default.
- Add extra controls for external, sensitive, destructive, or irreversible actions.
- Bound retries and handle invalid model output without an endless loop.
- Keep a clear way to stop execution.
- Treat the ability to choose among permitted actions as separate from the ability to change its own permissions.

## 9. Initial technical approach

The initial stack is expected to be Python, Ollama, a locally hosted language model, Pydantic, and SQLite or ordinary local files.

Model choice should depend on the available hardware and measured quality, latency, memory requirements, and reliability. Workshop topics such as local Llama execution, orchestration frameworks, structured outputs, vector databases, and graph-based retrieval are useful engineering options, but their use does not in itself establish intrinsic motivation or autonomy.

Begin with direct Python orchestration rather than introducing a multi-agent framework by default. Add a framework only when it solves a demonstrated problem.

## 10. Evaluation

Potential evaluation dimensions:

- **Initiative:** does the agent propose relevant activities without a new user prompt?
- **Diversity and repetition:** does it avoid both aimless randomness and unproductive loops?
- **State sensitivity:** do controlled changes to internal variables affect choices as hypothesized?
- **Continuity:** does useful information survive restarts and affect later decisions?
- **Functional adaptation:** do outcomes improve subsequent choices or task performance?
- **Traceability:** can a decision be reconstructed from its state, inputs, policy, and recorded result?
- **Robustness:** how does the loop handle invalid output, unavailable models, and failed actions?

Record the model, prompt, configuration, relevant state, proposal, selected action, outcome, and errors for each experiment. Compare a baseline with a modified mechanism while holding other variables as constant as practical.

## 11. Proposed development sequence

1. Finalize the initial documentation and hypotheses.
2. Establish a minimal local conversation baseline and verify Ollama connectivity.
3. Introduce structured action proposals and validation, initially without external execution.
4. Build a bounded persistent loop with complete event logging.
5. Add and evaluate one motivation variable at a time.
6. Test whether memory changes decisions and outcomes.
7. Expand the action set or memory architecture only when justified by evidence.

## 12. Open questions

- Which locally runnable model provides the best trade-off on the available hardware?
- What is the smallest persistent state that meaningfully improves continuity?
- How should energy, boredom, curiosity, and progress be operationalized?
- How can useful initiative be distinguished from novelty-seeking or random activity?
- At what point does simple memory become insufficient?
- Which actions can be safely automated, and which require explicit approval?
- Which hypotheses about consciousness can be investigated behaviorally, and which remain beyond what these experiments can establish?

## 13. Initial decision record

- Create a new repository instead of assuming the older MiniIA architecture should be refactored.
- Use MiniIA as a source of historical lessons, not a mandatory implementation template.
- Avoid defining a complete personality or a fixed set of interests in advance.
- Separate model proposals, validation, execution, state updates, and logging.
- Start with simple, inspectable persistence and a reproducible baseline.
- Evaluate autonomy experimentally without claiming that it proves consciousness.
