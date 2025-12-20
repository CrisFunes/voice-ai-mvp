# Contributing

Thanks for your interest in contributing.

## Quick start

1) Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\Activate.ps1
```

2) Install dependencies

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

3) Configure environment variables

- Copy `.env.example` to `.env`
- Fill in required keys

Important: `config.py` validates keys on import. Missing keys will fail tests early.

## Running tests

```bash
pytest -v
```

Notes:
- `tests/test_twilio_manual.py` is a manual interactive script (not an automated test).

## Project rules / non-negotiables

- **Receptionist role only**: the agent must not provide fiscal/accounting/legal advice.
  - Tax keywords must be rejected and routed to booking / human contact.
  - See `prompts.py` (`RECEPTIONIST_SYSTEM_PROMPT`, `TAX_QUERY_REJECTION`).
- **LangGraph state machine**: do not bypass `ConversationState`.
  - All nodes must read/write through the state.
- **Service layer**: instantiate services via `ServiceFactory` (`services/factory.py`).
  - Do not instantiate services directly.
- **DB sessions**: use `get_db_session()` from `database.py` and commit explicitly for writes.
- **Italian outputs**: user-facing responses should be in Italian (professional, formal “Lei”).
- **Voice constraints**: keep spoken responses short (Twilio TTS latency). Aim for <300 chars when feasible.

## Development workflow

- Prefer small, focused PRs.
- Keep changes aligned with existing patterns (factory + DB session context manager).
- If you change behavior, add/adjust tests in `tests/`.

## Code style

- Keep functions small and readable.
- Avoid unnecessary new abstractions.
- Log with `loguru` where it helps diagnose production issues (Twilio webhooks, orchestration transitions).

## Security

- Never commit `.env`, API keys, or credentials.
- Do not log secrets.
