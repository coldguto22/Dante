# Item 6 design: controlled ablations and observability

**Status:** implemented and tested  
**Date:** 2026-11-05

## Problem

The current trace records configured temperature and seed, but not the effective
context window or Ollama's prompt/evaluation counts. The hypotheses that model
size, reflection temperature, or structured-field order affect reflection
quality have not been tested independently. The item must change one variable at
a time and must not turn model output into a quality claim.

## Expected behavior and order

### 1. Observability only

Add configurable `DANTE_NUM_CTX` with a 2048-token default and pass it to
Ollama as `num_ctx`. Verify the installed `ollama` client's response attributes before using them.
Record `prompt_eval_count` and `eval_count` in the relevant prompt event metadata,
without storing message text beyond the existing event behavior. If the client
does not expose an attribute, record an explicit unavailable value rather than
silently guessing.

### 2. Model arm

Compare the configured 3B model with an approximately 8B and approximately 14B
Q4 model only after checking local availability and VRAM use on the maintainer's
12 GB GPU. The comparison keeps post-item-4 temperature, seed, prompt, schema,
history mode, and fresh databases fixed. No model is assumed to fit or to be
installed.

### 3. Reflection temperature arm

Add optional `DANTE_REFLECTION_TEMPERATURE`, defaulting to
`DANTE_TEMPERATURE`. Proposal generation keeps its existing temperature while
reflection execution uses the override. This isolates reflection decoding
temperature without changing proposal selection or history.

### 4. Structured field-order arm

Reorder `InitiativeReflection` fields in a separate experimental arm only. The
field semantics and validation remain unchanged. The arm is not combined with a
model, temperature, or prompt change.

## Verification protocol

Each arm uses fixed seeds, fresh databases, the same cycle limit, and at least
10 paired runs against its baseline. Every run records the exact model,
temperature, seed, context configuration, and availability/measurement status.
Item 4's deterministic checks are collected automatically; a manual sample is
reviewed with the existing rubric in `docs/INITIATIVE_EXECUTION.md`.

Results are reported in a dated table with observed outputs, automatic check
statuses, and manual notes. If Ollama or candidate models are unavailable, code
and protocol may be delivered, but live results are explicitly unverified and
no numbers are fabricated.

## Risks and boundaries

- Ollama attribute names may differ by installed client version; verify before
  implementation and use explicit unavailable values.
- VRAM pressure can cause load failures or distort latency; availability and
  memory use are observations, not assumed capabilities.
- Ten pairs per arm provide an initial diagnostic comparison, not a general
  model-quality conclusion.
- Field order can change formatting behavior without improving reasoning; report
  that distinction.
- No automatic reward, semantic score, or claim about autonomy or consciousness
  is introduced.

## Stop conditions

Stop an arm when its requested variable cannot be held fixed, the model cannot
be loaded reliably, telemetry is unavailable and would invalidate the intended
measurement, or a run would require unbounded retries. Preserve partial logs
only as clearly labeled incomplete observations.

## Removal criterion

Remove observability or an ablation arm if it does not produce reliable,
interpretable measurements after the protocol, or if it adds complexity without
answering a stated hypothesis. Record that decision as an engineering
evaluation, not as evidence for or against consciousness.

## Implementation note (2026-11-05)

`DANTE_NUM_CTX` and `DANTE_REFLECTION_TEMPERATURE` are implemented. Proposal
calls use `DANTE_TEMPERATURE`; the reflection override is passed only to
reflection calls. Initiative prompt metadata records effective temperature,
its source, configured reflection temperature, context window, seed, model, and
Ollama structured-call telemetry (`prompt_eval_count`, `eval_count`, and an
explicit availability status). The model-size and field-order arms remain
protocol-only because they require controlled local model availability and
separate experimental runs; no live comparative numbers were fabricated.

The conversation module uses this same model and context configuration. A live
conversation attempt with no context override failed because Ollama could not
allocate roughly 6 GiB for the KV cache on the 12 GB GPU. Setting the default
`DANTE_NUM_CTX=2048` allowed `llama3.1:8b` to answer from an isolated test
database. `OllamaLLM.chat()` now includes the first line of the server error in
its user-visible diagnostic so connection failures and model-load failures can
be distinguished. This confirms startup and one response, not answer quality.
