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

## Technical direction

The initial implementation is expected to use:

- **Python** for the agent loop and experimental infrastructure.
- **Ollama** to run a selected language model locally.
- **Pydantic** for validating structured model proposals.
- **SQLite and ordinary files** for initial state persistence and event logs.

The exact model should be selected based on available hardware and measured quality, latency, memory use, and stability. Frameworks such as CrewAI and vector or graph databases can be evaluated later if a concrete need justifies their added complexity.

## Planned structure

```text
.
├── README.md
├── .gitignore
├── docs/
│   └── FOUNDATIONS.md
├── experiments/
└── tests/
```

## Milestones

1. Document hypotheses, constraints, and evaluation criteria.
2. Build a minimal local conversational baseline and verify model connectivity.
3. Require structured, validated activity proposals without granting them unrestricted execution.
4. Add a controlled loop that records state, proposal, decision, action, and outcome.
5. Test persistence and vary one motivation mechanism at a time.
6. Add tools and more sophisticated memory only when experiments demonstrate a need.

## Safety and scope

Begin with a small, explicit set of permitted actions. Keep execution separate from proposal generation, record failures, and preserve a way to stop the loop. Access to files, shell commands, navigation, external services, or irreversible operations must be considered and constrained explicitly before it is introduced.

## Current status

**Documentation and experimental design.** No functional agent implementation is claimed at this stage.
