## Why

The project directory structure has been scaffolded but contains no runnable code. Before any agents, scrapers, or AI logic can be built (Phases 2–8), both applications need to boot, the database connection must work, and developers need a single verified command to confirm the stack is healthy. Phase 1 delivers that baseline.

## What Changes

- Initialize a React + Vite + Tailwind CSS project inside `frontend/`.
- Initialize a FastAPI application inside `backend/` with the layered structure described in `docs/architecture.md` (`api/`, `services/`, `agents/`, `tools/`, `database/`, `core/`).
- Create `backend/core/config.py` to load environment variables via pydantic-settings.
- Create a `.env.example` at the project root documenting all required env vars for local development.
- Set up an async MongoDB connection using Motor in `backend/database/connection.py`.
- Implement `GET /api/v1/health` — returns server status, database connectivity, and a timestamp (as defined in `docs/api.md`).

## Capabilities

### New Capabilities
- `backend-app`: FastAPI application skeleton with project structure, CORS middleware, and API router mounting.
- `database-connection`: Async MongoDB connection via Motor with health-check verification.
- `env-config`: Centralized environment variable loading using pydantic-settings with a documented `.env.example`.
- `health-endpoint`: `GET /api/v1/health` endpoint returning server status, DB connectivity, and timestamp.
- `frontend-app`: React + Vite + Tailwind CSS project scaffold in `frontend/`.

### Modified Capabilities
_(none — no existing specs to modify)_

## Impact

- **New dependencies (backend):** `fastapi`, `uvicorn`, `motor`, `pydantic-settings`, `python-dotenv`.
- **New dependencies (frontend):** `react`, `vite`, `tailwindcss` (and their standard peer deps).
- **New files:** `backend/main.py`, `backend/core/config.py`, `backend/database/connection.py`, `backend/api/v1/health.py`, `.env.example`, plus Vite/Tailwind boilerplate in `frontend/`.
- **APIs added:** `GET /api/v1/health`.
- **No breaking changes** — this is a greenfield setup.
