# Project Documentation

This folder contains delivery-ready documentation for the project.

## Contents

- `00_PROJECT_CORE.md` — high-level project architecture and current state.
- `MOCKUP_FLUJOS_CONVERSACION.md` — conversation flow mockups / user journey examples.
- `ANALISIS_CAPACIDADES_Y_REFACTORING.md` — refactoring notes and capability analysis.

## Notes

- Historical scripts and experiments remain in `archive/`.
- The main runtime entrypoint is `server.py` (Twilio Voice webhooks).
- The orchestration logic is in `orchestrator.py` (LangGraph state machine).
