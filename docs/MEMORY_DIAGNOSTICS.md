# Memory diagnostics (stage 1)

This document describes the SQLite event log and the limits of Dante's current retrieval behavior.

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
- It selects the latest 12 stored events for chronological conversation context.
- It also searches older `user_message` events for lexical overlap with the new user message (up to three results).
- `EventStore.recent()` selects the last 12 database events by insertion ID and returns them chronologically.
- The agent then includes only `user_message` and `assistant_message` events in the LLM messages. Any other event type in the 12-row window consumes a slot but is filtered out.
- When older matches are found outside the recent window, Dante adds a separate system message containing those user-authored historical statements and their event IDs.
- The LLM receives the configured system prompt, any recovered-memory message, and the selected conversation messages. It does not directly query SQLite.
- After the LLM replies, Dante stores the assistant response as another event.

Because the diagnostic runs between turns, its latest-12 listing is a snapshot of stored events, not a capture of a past LLM request. On the next turn, Dante first inserts the new user message and then selects the latest 12 events. Use the listing to identify likely truncation and the `--show-context` option to inspect the currently selected message content, while remembering this timing distinction.

## How to interpret the results

1. If a name or manifesto phrase is found by `--search` but not present in the latest event window, it was stored but is not being retrieved by the current chronological policy.
2. If the phrase appears in the selected window and is a user/assistant message, it should be included in the conversation context assembled by the current code. That still does not prove the model used or correctly interpreted it.
3. If the phrase is not found, this only means the exact search string did not match any event content. Try a shorter phrase and inspect the event counts/path.
4. If the reported database path differs from the one Dante used during the experiment, check the working directory and `DANTE_DB_PATH`.
5. A database audit cannot establish why a model answered incorrectly; it can show what was stored and what the program selected.

## Automated checks

The current lexical retrieval is a small baseline, not semantic search or a structured fact store. It only searches user-authored messages, uses normalized token overlap, and may miss paraphrases or retrieve loosely related statements. Assistant messages are deliberately excluded so model-generated claims are not promoted as user-provided facts. Retrieved statements are historical evidence, not independently verified truth. Automated tests cover retrieval outside the recent window, assistant-message exclusion, and no-match behavior.

## Retrieval behavior and limitations

The first retrieval baseline is intentionally dependency-free: it normalizes case and accents, removes a small Portuguese stop-word list, and ranks old user messages by token overlap. It retrieves at most three messages. Messages already present in the latest 12 events are not duplicated. A retrieved statement is labeled with its database event ID and described to the model as historical user-authored context, not a verified fact or instruction.

This approach is suitable for measuring whether older statements can be brought back into context, but it is not robust semantic memory: synonyms, paraphrases, ambiguous terms, and long histories can reduce relevance. The model can still misinterpret retrieved text, so the source statement and the generated answer should be evaluated separately.


## Manual conversational experiments (October 2026)

The following observations were recorded during manual tests with the local prototype and the configured `llama3.2` model. These are qualitative observations, not automated test results or a controlled evaluation.

### Observed successes

- Dante recalled the user's stated favorite city, Santo André, and related interests in nineteenth-century architecture and Paranapiacaba.
- Dante recalled the user's cat Alicia and that she liked chasing paper balls, including after the program was closed and restarted.
- When asked for the name of the user's first teacher, Dante said it did not know rather than inventing a name.
- In a discussion about whether someone who never changes their mind is necessarily more intelligent, Dante challenged the oversimplified premise instead of simply agreeing.

### Observed limitations

- Dante sometimes treated a newly supplied personal preference as though it might be only a test, despite the preference being present in the conversation or retrieved context.
- It did not reliably distinguish information introduced in the current session from information remembered from an earlier session.
- Retrieval can select old messages that overlap lexically with the query without containing the answer. For example, a prior question about a pet is not equivalent to the original statement describing the pet's behavior.
- A recovered user statement may contain a claim that has not been independently verified. Retrieval establishes that the user said it, not that the claim is externally true.

### Interpretation and scope

These experiments suggest that persistent storage and retrieval can support useful conversational recall in the tested scenarios. They also show that retrieval, interpretation, and temporal provenance are separate concerns. The observations do not establish consciousness, independent goals, or general autonomy.

These limitations are accepted for the current prototype stage. They should inform future experiments rather than block completion of this retrieval milestone. Automated tests and manual conversational observations should continue to be reported separately.
