# Voice AI Receptionist - AI Agent Instructions

This is a **Twilio-based voice AI receptionist** for an Italian accounting firm. The agent is a **professional receptionist** (NOT a tax advisor) that handles appointments, routing, and office info—but explicitly rejects tax/fiscal queries.

## Architecture: LangGraph State Machine

The core conversation flow uses **LangGraph** (`orchestrator.py`) with a 5-node state machine:

```
welcome_node → classify_intent_node → execute_action_node → generate_response_node → END
                      ↓
              (if requires_followup, loops back to classify)
```

**State object** (`ConversationState` TypedDict) is the single source of truth passed between nodes. Never bypass it—all context lives here (user_input, intent, entities, conversation_history, client_id, response, etc.).

### Key Components

- **`orchestrator.py`**: LangGraph orchestrator, intent classification (4 intents: `APPOINTMENT_BOOKING`, `ACCOUNTANT_ROUTING`, `OFFICE_INFO`, `LEAD_CAPTURE`, `UNKNOWN`)
- **`services/`**: Service layer (BookingService, ClientService, OfficeInfoService, LeadService, RoutingService)
- **`services/factory.py`**: Factory pattern for creating service instances (supports `mock`/`real` modes for testing)
- **`models.py`**: SQLAlchemy models (Client, Accountant, Appointment, OfficeInfo, Lead, CallLog)
- **`database.py`**: DB session management, health checks, context managers
- **`server.py`** / **`server_backup.py`**: Flask/Twilio webhooks (`/voice/incoming`, `/voice/gather`, `/voice/status`)
- **`voice_handler.py`**: OpenAI Whisper (STT) + TTS for Italian voice I/O
- **`prompts.py`**: Centralized prompts (`RECEPTIONIST_SYSTEM_PROMPT`, `TAX_QUERY_REJECTION`)
- **`config.py`**: Dual-provider LLM config (Anthropic Claude 3.5 Sonnet primary, OpenAI GPT-4o fallback)

## Critical Patterns

### 1. Receptionist Role (NOT Tax Advisor)
**The agent explicitly rejects tax/fiscal queries.** If a user asks about IVA, IRES, scadenze, deduzioni, etc., respond with `TAX_QUERY_REJECTION` prompt and suggest booking an appointment with a real accountant. See `orchestrator.py:classify_intent_node()` for tax keyword detection pattern.

### 2. Service Layer Architecture
Services are **injected via factory** (`ServiceFactory`). Always use the factory pattern:
```python
from services.factory import ServiceFactory
from database import get_db_session

with get_db_session() as db:
    factory = ServiceFactory(mode="real", db_session=db)
    booking_service = factory.create_booking_service()
    result = booking_service.check_availability(...)
```

Never instantiate services directly. The factory handles dependency injection and mode switching (mock vs real).

### 3. Database Sessions
Use `get_db_session()` context manager from `database.py`:
```python
with get_db_session() as db:
    # do work
    db.commit()  # explicit commit
```
Sessions auto-close on context exit. **Always commit explicitly** for writes.

### 4. Italian Language First
- All user-facing responses in **Italian** (professional, Northern Italian tone)
- Voice config: `language="it-IT"`, `voice="Google.it-IT-Standard-A"` (Twilio TTS)
- STT: OpenAI Whisper with `language="it"`
- Use natural phrasing (e.g., "Buongiorno", "Arrivederci", formal "Lei" form)

### 5. Twilio Integration
Webhooks follow this flow:
1. `/voice/incoming` → sends greeting, sets up `<Gather>` for STT
2. `/voice/gather` → processes transcript via orchestrator, returns TwiML with response + next gather
3. Loop continues until farewell detected or timeout

**Response truncation**: Keep AI responses <300 chars to minimize TTS latency (see `server_backup.py:242`).

### 6. Testing Conventions
- Tests use `pytest` with descriptive names: `test_<feature>_<scenario>.py`
- Service tests mock DB via `ServiceFactory(mode="mock")`
- Integration tests use real DB (`ServiceFactory(mode="real")`) with rollback
- Conversation flows documented in `MOCKUP_FLUJOS_CONVERSACION.md`

## Development Workflows

### Running the Server
```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Start Flask server (port 5000)
python server.py

# Expose with ngrok (for Twilio webhooks)
ngrok http 5000
```

### Database Operations
```python
# Seed test data
python seed_data.py  # Creates 50 clients, 10 accountants, 30+ appointments

# Verify DB health
from database import check_database_health
check_database_health()  # Returns dict with table counts
```

### Running Tests
```powershell
# All tests
pytest

# Specific test file
pytest test_booking_e2e.py -v

# With logging
pytest --log-cli-level=INFO
```

### Environment Setup
Required `.env` keys:
- `OPENAI_API_KEY` (for Whisper STT, TTS, fallback LLM)
- `ANTHROPIC_API_KEY` (primary LLM: Claude 3.5 Sonnet)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` (for voice integration)
- `FLASK_SECRET_KEY` (session management)

## Common Pitfalls

1. **Don't bypass the state machine**: Always process input through `orchestrator.process(user_input)`, never call services directly from webhooks
2. **Don't enable RAG**: The `rag_engine.py` exists but is **disabled** post-Sprint 1 (agent doesn't answer tax queries)
3. **Don't forget intent rejection**: Tax keywords trigger `UNKNOWN` intent + rejection message, NOT `TAX_QUERY` (which was removed)
4. **Session management**: Flask `call_sessions` dict is in-memory (fine for MVP, use Redis for production)
5. **Enum storage**: SQLAlchemy enums stored as **strings** for SQLite compatibility (see `models.py`)

## Key Files for Context

- **Architecture**: [00_PROJECT_CORE.md](00_PROJECT_CORE.md) (comprehensive project state)
- **Conversation flows**: [MOCKUP_FLUJOS_CONVERSACION.md](MOCKUP_FLUJOS_CONVERSACION.md) (user journey examples)
- **Sprint history**: [SPRINT_1_COMPLETADO.md](SPRINT_1_COMPLETADO.md) (tax query removal changelog)
- **Service patterns**: [services/booking_service.py](services/booking_service.py), [services/factory.py](services/factory.py)
- **Orchestrator logic**: [orchestrator.py](orchestrator.py) (nodes: lines 56-899)
- **Twilio webhooks**: [server_backup.py](server_backup.py) (reference implementation)

## Project Status
- **Current phase**: Day 5 / Sprint 1 complete (85% done)
- **Next**: Twilio production integration, performance optimization
- **Tech stack**: Python 3.10+, Flask, LangGraph, SQLAlchemy, Twilio, OpenAI, Anthropic
- **Database**: SQLite (dev), PostgreSQL-ready (prod)
