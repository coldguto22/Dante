# Memory diagnostics (stage 1)

This step investigates the existing SQLite event log without changing Dante's memory or retrieval behavior.

## Run locally

From the repository root, with the project's virtual environment active and dependencies installed:

```powershell
python -m dante.memory_audit
```

The tool uses the same `DANTE_DB_PATH` setting as Dante (default: `data/dante.sqlite3`). It opens the database in read-only mode and reports the resolved path, event counts, and the latest 12 stored events. It does not create a missing database or write to an existing one.

Search for a fact or phrase across the full event log:

```powershell
python -m dante.memory_audit --search "Otávio"
python -m dante.memory_audit --search "Guto"
python -m dante.memory_audit --search "Cada conversa te molda"
```

To print full user/assistant message content in the selected window, explicitly opt in:

```powershell
python -m dante.memory_audit --show-context
```

Be aware that this can print private conversation content in the terminal. The default report truncates event previews; search results and `--show-context` intentionally print matching/full text.

## What the current implementation does

- `DanteAgent.respond()` stores the incoming user message before retrieving context.
- It calls `EventStore.recent(limit=12)`.
- `EventStore.recent()` selects the last 12 database events by insertion ID and returns them chronologically.
- The agent then includes only `user_message` and `assistant_message` events in the LLM messages. Any other event type in the 12-row window consumes a slot but is filtered out.
- The LLM receives the configured system prompt plus the selected conversation messages. It does not directly query SQLite.
- After the LLM replies, Dante stores the assistant response as another event.

Because the diagnostic runs between turns, its latest-12 listing is a snapshot of stored events, not a capture of a past LLM request. On the next turn, Dante first inserts the new user message and then selects the latest 12 events. Use the listing to identify likely truncation and the `--show-context` option to inspect the currently selected message content, while remembering this timing distinction.

## How to interpret the results

1. If a name or manifesto phrase is found by `--search` but not present in the latest event window, it was stored but is not being retrieved by the current chronological policy.
2. If the phrase appears in the selected window and is a user/assistant message, it should be included in the conversation context assembled by the current code. That still does not prove the model used or correctly interpreted it.
3. If the phrase is not found, this only means the exact search string did not match any event content. Try a shorter phrase and inspect the event counts/path.
4. If the reported database path differs from the one Dante used during the experiment, check the working directory and `DANTE_DB_PATH`.
5. A database audit cannot establish why a model answered incorrectly; it can show what was stored and what the program selected.

## Automated checks

The tests for this step cover the read-only audit output and make the current 12-event boundary explicit. They document existing behavior; they do not add relevance-based retrieval, structured profile memory, or a fix for forgetting old facts.
