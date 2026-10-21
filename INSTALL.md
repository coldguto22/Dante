# Local installation and execution

Dante is an early prototype. It supports terminal conversation with a local Ollama model and records conversation events in SQLite. It does not yet run an autonomous background loop or execute proposed external actions.

## Requirements

- Python 3.11 or newer
- [Ollama](https://ollama.com/) installed and running locally
- A model downloaded in Ollama

## Setup

From the repository root, create and activate a virtual environment.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Linux/macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Pull the model configured by `DANTE_MODEL` in `.env`, for example:

```bash
ollama pull llama3.2
```

Change the model name to match a model installed locally.

## Run

Ensure Ollama is running, then execute from the repository root:

```bash
python -m dante
```

Type `/exit` to end the session. The database defaults to `data/dante.sqlite3`; local databases are excluded from version control.

## Tests

```bash
python -m pytest
```

Tests use simulated model responses where possible and should not require a running Ollama server.

## Current limitations

- This is a terminal conversation, not an autonomous scheduler.
- The model does not execute external actions.
- Events persist, but this is not semantic retrieval or long-term learning.
- The example model is a starting point, not a hardware-specific recommendation.
