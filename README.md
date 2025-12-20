# Voice AI Receptionist (Twilio + LangGraph) — MVP

A Twilio-based voice receptionist for an Italian accounting firm (**studio commercialista**). It answers calls, books appointments, routes callers to the right accountant, and provides basic office info.

Important: this agent is **NOT a tax advisor**. Fiscal/tax/accounting/legal questions are **politely rejected** and the caller is invited to **book an appointment** with a professional.

## What it does (and what it does not)

- ✅ Appointment booking (creates/validates slots and writes to the DB)
- ✅ Call routing (identify caller when possible, route to accountant/specialist)
- ✅ Office info (hours, address, contact from the DB)
- ✅ Lead capture (collects information for new prospects)
- ✅ Voice loop (Twilio Gather STT) in Italian, short answers
- ❌ No fiscal/accounting/legal advice (by design)

## Architecture

The core flow is a LangGraph state machine in [orchestrator.py](orchestrator.py):

`welcome_node → classify_intent_node → execute_action_node → generate_response_node → END`

All context lives in `ConversationState` (TypedDict). Services are created via `ServiceFactory` in [services/](services/), supporting `mock`/`real` modes.

Project docs are in [docs/](docs/).

## Requirements

- Python 3.10+
- API keys / accounts:
  - OpenAI (embeddings utilities; optional voice components)
  - Anthropic (primary LLM) or OpenAI as fallback
  - Twilio (Voice webhooks)

## Install

```bash
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Configuration (.env)

This repo expects environment variables in `.env` (never committed).

1) Copy `.env.example` → `.env`
2) Fill in keys

Notes:
- [config.py](config.py) validates keys **on import**. Missing keys will fail fast.
- `SERVICE_MODE=real` uses the real DB-backed services; `mock` uses mock implementations.

## Run (Twilio Voice Webhooks)

Start Flask on `http://localhost:5000`:

```bash
python server.py
```

Main endpoints:
- `POST /voice/incoming` (greeting + `<Gather>`)
- `POST /voice/gather` (processes Twilio `SpeechResult`)

### Expose locally with ngrok

```bash
ngrok http 5000
```

Twilio Console → Phone Numbers → Voice webhook:
- Method: `POST`
- URL: `https://<your-ngrok>/voice/incoming`

## Database

- SQLAlchemy models: [models.py](models.py)
- Session management: [database.py](database.py) (`get_db_session()`)
- Default DB: SQLite (`demo_v2.db`) unless you set `DATABASE_URL`

Initialize tables:

```bash
python -c "from database import init_db; init_db()"
```

## Tests

```bash
pytest -v
```

Notes:
- Some tests import modules that import [config.py](config.py), so `.env` must exist.
- `tests/test_twilio_manual.py` is a **manual interactive script**, not an automated test.

## Repository layout (quick)

- [server.py](server.py): Flask + Twilio webhooks
- [orchestrator.py](orchestrator.py): LangGraph orchestrator + intent handling
- [services/](services/): service layer (factory-based)
- [database.py](database.py), [models.py](models.py): DB
- [prompts.py](prompts.py): receptionist prompt + tax-query rejection copy

## Delivery notes

- Secrets are gitignored (see [.gitignore](.gitignore)).
- `chroma_db/`, `logs/`, `temp/`, `venv/` are generated and should not be committed.
- Contribution guidelines: [CONTRIBUTING.md](CONTRIBUTING.md)
- Release notes: [RELEASE_NOTES.md](RELEASE_NOTES.md)