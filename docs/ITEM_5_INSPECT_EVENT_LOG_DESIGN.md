# Item 5 design: read-only `inspect_event_log`

**Status:** implemented and tested  
**Date:** 2026-11-05

## Problem

Execute mode currently performs only a reflection call. A reflection may propose a
check, but no program-owned check runs, so `check_was_actually_run` remains empty
in the review export and `progress_verified` remains false. This prevents a
bounded experiment from distinguishing a model suggestion from an observed
event-log fact.

## Expected behavior

Add one code-owned, read-only initiative capability named `inspect_event_log`.
The model may request one of a fixed set of queries, but it may not provide SQL.
The executor validates the request, runs the corresponding parameterized query,
records the request and result as initiative events, and supplies the structured
result to the current cycle. The capability has `external_effects=False` and
does not grant access to arbitrary files, shell commands, web services, or the
main conversation database.

### Fixed query catalog

The implementation will expose only these query names:

- `event_counts`: counts by event type for the selected experiment database;
- `recent_results`: the last `n` `initiative_result` events, newest first;
- `cycle_result`: whether one exact `cycle_id` has an `initiative_result`;
- `recent_decisions`: the last `n` `initiative_decision` events, newest first.

All query parameters are bound values. `n` will be an integer from 1 through 10.
`cycle_id` will be a non-empty bounded string and will be matched exactly.
Returned records will be bounded and omit raw conversation content.

### Schema and permissions

Add a Pydantic request schema with a literal query name and constrained
parameters. The action type will be distinct from `reflect`, and the registry
will mark it available with `external_effects=False`; authorization still
requires the dedicated executor path.

The executor will accept only a configured experiment database path. It will
open SQLite using the same read-only URI pattern as `memory_audit`
(`file:<resolved-path>?mode=ro`), reject missing or non-SQLite paths, and avoid
creating or mutating the database. The main conversation database must be
rejected by an explicit path check or an experiment-runner-owned database
allowlist, rather than relying on the model to choose safely.

Add two event types to the model literal:

- `initiative_check`: validated query request and cycle linkage;
- `initiative_check_result`: code-owned result, status, and error metadata.

The result event must not include unrestricted SQL or unbounded event content.
Malformed requests, unsupported query names, missing databases, and SQLite
errors will produce an explicit error result/event and will not be reported as a
successful check.

## Verification plan

1. Schema tests reject unknown query names, missing parameters, `n=0`, `n>10`,
   overlong cycle IDs, and extra/unbounded query text.
2. Authorization tests accept only the new registered action with
   `requires_external_action=False`; web, shell, filesystem, and arbitrary
   external requests remain rejected.
3. Read-only tests use a temporary experiment database, verify all four fixed
   queries, assert that row counts and result shapes are bounded, and confirm
   the source database is unchanged.
4. Failure tests cover missing databases, malformed requests, unsupported
   queries, and a request targeting the main conversation database.
5. Integration tests assert that a successful `initiative_check_result` exists
   before `check_was_actually_run` becomes `1`.
6. Tests explicitly assert that `progress_verified` remains false. It can only
   change in a later item that adds an independent verifier; a model response or
   the mere existence of a check result is not proof of progress.
7. Exporter tests preserve legacy rows and expose the check status/result without
   reading or modifying the source database.

## Stop conditions and failure behavior

The loop remains bounded to ten cycles and one check per selected action. A
failed or timed-out read-only query records an error and does not retry
indefinitely. The loop may continue to the next bounded cycle only if the
existing runner policy allows it; no failure is converted into a success-shaped
empty result. The capability remains unavailable until its registry, executor,
event, and tests are all present.

## Removal criterion

Remove or replace this capability if controlled runs show that fixed event-log
inspection does not produce a measurable reduction in false absence claims,
improve evidence-grounded selections, or enable independently verifiable
progress after the planned verifier exists. Any removal must preserve the event
history and document the result as an observed experiment, not as evidence that
initiative or consciousness was established.

## Implementation note (2026-11-05)

The fixed request schema, registry entry, read-only inspector, check/result
events, exporter fields, and regression tests are implemented. The full suite
passes with 70 tests. No independent verifier was added, so
`progress_verified` remains false.
