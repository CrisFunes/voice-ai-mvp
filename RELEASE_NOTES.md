# Release Notes

## v1.0.0 — 2025-12-20

### Summary

Initial project delivery for a Twilio-based **Voice AI Receptionist** for an Italian accounting firm. The agent manages appointments, call routing, and office information, and **explicitly rejects** fiscal/tax/accounting/legal advisory requests.

### Key features

- Twilio Voice webhooks (Flask): `/voice/incoming` and `/voice/gather`.
- LangGraph orchestrator state machine with a single source of truth state (`ConversationState`).
- Intent handling for:
  - Appointment booking
  - Accountant routing
  - Office information
  - Lead capture
  - Unknown/clarification
- Guardrails: tax/fiscal queries are rejected and redirected to appointment booking.
- SQLAlchemy database layer (SQLite default, PostgreSQL-ready via `DATABASE_URL`).
- Test suite validating end-to-end flows (booking/routing/office info/tax rejection).

### Documentation

- Root documentation: `README.md`
- Project docs moved to `docs/` (architecture notes, conversation flow mockups, refactoring analysis)
- Environment template added: `.env.example`

### Known limitations / MVP notes

- In-memory call session storage in `server.py` (use Redis or a shared store for production).
- `config.py` validates API keys on import (tests and runtime require `.env` present).
- Production hardening (auth, rate limiting, observability, deployment) is out of scope for MVP delivery.
