# JobPilot AI

AI-powered multi-agent job search assistant that automates job discovery, application tracking, resume tailoring, and interview preparation using locally-hosted LLMs and browser automation.

## Tech Stack

- React + Vite + Tailwind CSS
- FastAPI (Python)
- MongoDB
- LangChain + LangGraph
- Ollama
- Playwright

## Folder Map

- `backend/` — FastAPI server, AI agents, database models, and business logic
- `frontend/` — React client application (not active until backend is stable)
- `docs/` — Architecture, API, database, and feature documentation
- `specs/` — Phase-wise implementation specifications
- `prompts/` — System prompt templates for each AI agent
- `scripts/` — Utility and automation scripts
- `openspec/` — OpenSpec change management and project context

## Agent Rules

1. Always read this file first before starting any task.
2. Do not scan the full repo unless explicitly told to.
3. Check `docs/completed_features.md` before making changes to see what already exists.
4. Treat `docs/database.md` and `docs/api.md` as source of truth for data shapes and endpoints.
5. Work only within the current phase defined in `docs/phases.md`.
6. Backend is being built before frontend — do not touch `frontend/` unless explicitly asked.
