# Agent Instructions for Dante

These instructions apply to work in this repository. They are intended to be useful across coding agents; follow any additional tool-specific instructions required by the environment.

## 1. Read the project context

Before proposing architectural changes or implementing a substantial feature, read:

1. `README.md` — project overview, research questions, current status, and broad technical direction.
2. `docs/FOUNDATIONS.md` — foundational concepts, operational definitions, hypotheses, and initial decisions.
3. `docs/TRANSITION_FROM_MINIIA.md` — lessons from the MiniIA experiments, what to preserve or defer, known failure modes, and the transition plan.

The transition document may be on the `docs/miniia-transition` branch until its pull request is merged. If it is absent from the checked-out branch, do not assume it does not exist: consult that branch or ask for the document when repository access does not permit it.

For task-specific work, inspect the relevant source files, tests, configuration, and documentation. Do not load or reproduce every document by default when a smaller, focused context is sufficient.

## 2. Preserve the project's purpose

Dante is an experimental research and engineering project investigating agent initiative, continuity, internal-state-driven activity selection, and adaptation from outcomes. It is not merely a generic assistant project.

- Treat autonomy, intrinsic motivation, homeostasis, and consciousness-related questions as research topics, not established capabilities or conclusions.
- Do not claim that fluent self-description, simulated feelings, reflection, memory, or unsupervised activity proves subjective consciousness.
- Distinguish observable behavior from the model's explanation of that behavior.
- Do not hard-code a complete personality or fixed set of interests without a clear experimental reason.
- Keep the language model separate from the program logic that validates proposals, applies permissions, executes actions, records outcomes, and updates state.

## 3. Verify capabilities instead of assuming them

The current implementation and its tests are the source of truth for what the code can actually do.

- Inspect the relevant code and run appropriate tests before describing a capability as implemented.
- Clearly distinguish implemented behavior, planned work, hypotheses, and ideas.
- Do not infer internet access, screen perception, background activity, tool use, learning, or autonomous decision-making from a model's statements. Verify the actual integration and execution path.
- When investigating a failure, trace the complete path: configuration and gates, proposal, validation, selection, execution, observation, persistence, and tests, as applicable.
- Treat model-generated claims as untrusted output until independently checked.

## 4. Work incrementally and keep changes traceable

- Prefer the smallest change that answers a specific question or improves a measurable behavior.
- State the problem, expected behavior, and a way to verify the result before adding a substantial mechanism.
- Change one major variable or mechanism at a time when designing experiments.
- Add or update tests for new behavior and regression risks.
- Preserve useful existing documentation. Do not rewrite or replace documents merely to duplicate information.
- Avoid adding frameworks, services, databases, dependencies, or architectural layers without a concrete need and a clear benefit over the simpler alternative.
- Do not silently broaden the task or introduce unrelated refactors.
- Record important decisions, limitations, and known failure modes in the appropriate documentation.

## 5. Safety, permissions, and external actions

Model proposals are not authorization to execute an action.

- Keep proposal generation separate from action execution.
- Validate structured outputs and check each action against explicit programmatic permissions.
- Keep external actions disabled unless they have been deliberately designed, reviewed, and enabled for the relevant use case.
- Treat file access, shell commands, screen capture/OCR, browsing, external services, and irreversible operations as separate capabilities with explicit boundaries.
- Provide a clear stop mechanism for loops and background activity.
- For screen observation, prefer an explicit, visible, privacy-conscious design; do not enable continuous capture by default.
- Record relevant decisions, failures, and outcomes without unnecessarily collecting sensitive data.

## 6. Memory and evidence

- Preserve the provenance of remembered information where practical: distinguish user-provided facts, observations, model-generated interpretations, and hypotheses.
- Do not silently turn an inference into a fact or erase contradictions to make a profile appear consistent.
- Treat persistence as different from learning. Test whether retrieved information actually changes later decisions or outcomes.
- Prefer the existing simple storage and event-log approach until evaluation demonstrates a specific limitation.
- Do not introduce vector databases, elaborate consolidation, or other memory infrastructure solely because they are common in agent projects.

## 7. Testing and reporting

For each meaningful change:

1. Run the narrowest relevant tests first, then broader tests when practical.
2. Report the exact checks performed and whether they passed.
3. If a test could not be run, say so; do not imply it passed.
4. Include relevant limitations, unverified assumptions, and follow-up work.
5. Do not claim that mocked tests establish reliability with a real local model or external service.

Prefer deterministic tests for program logic and clearly identified integration tests for Ollama, network access, and other external dependencies. Experiments should be reproducible enough to compare outcomes.

## 8. Repository and documentation hygiene

- Follow the existing project structure and style unless there is a justified reason to change them.
- Keep secrets, credentials, local databases, personal data, and machine-specific configuration out of version control.
- Update installation instructions or examples when a change affects setup or usage.
- Keep the README concise and accurate about the current implementation status.
- When updating a research or decision document, distinguish source-supported facts, engineering inferences, hypotheses, and implemented-and-tested behavior.
- Do not merge branches, close pull requests, or make unrelated repository changes unless explicitly requested.

## 9. Suggested workflow

For a new task:

1. Identify the requested outcome and inspect the relevant repository state.
2. Read the context documents relevant to the task.
3. Summarize the existing behavior and the smallest proposed change.
4. Implement the change and tests without unrelated refactoring.
5. Run tests and inspect the final diff.
6. Report what changed, what was verified, and what remains uncertain.

When requirements or evidence are insufficient, ask a focused question or document the uncertainty rather than inventing a decision.
