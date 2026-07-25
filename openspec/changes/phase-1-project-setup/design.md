## Context

The backend project structure is scaffolded but empty. Phase 1 sets up the initial application frameworks (FastAPI for the backend, React + Vite + Tailwind CSS for the frontend), establishes the configuration mechanism using Pydantic Settings, configures an async connection to MongoDB using Motor, and exposes a `/api/v1/health` endpoint to verify that both the web server and the database connection are fully functional.

## Goals / Non-Goals

**Goals:**
- Boot up FastAPI backend application.
- Centralized configuration using `pydantic-settings` loaded from `.env` and documented in `.env.example`.
- Connect asynchronously to MongoDB via Motor driver.
- Expose a functional `GET /api/v1/health` endpoint verifying both server status and DB connection.
- Scaffold the React client using Vite and Tailwind CSS.

**Non-Goals:**
- Implement any scrapers, extraction logic, or database collections (jobs, users, etc.).
- Build any frontend UI beyond the basic scaffold.
- Implement any auth or agent/LLM orchestration.

## Decisions

### 1. Backend Framework: FastAPI
- **Choice**: FastAPI
- **Rationale**: Built-in async support, easy data validation with Pydantic, automatic OpenAPI documentation, and high performance.
- **Alternatives**: Flask (lacks async out-of-the-box, manual validation), Django (too heavy, synchronous by default).

### 2. Configuration Management: Pydantic Settings
- **Choice**: `pydantic-settings`
- **Rationale**: Validates type safety of environment variables at startup, preventing runtime errors. Automatically maps system environment variables and loaded `.env` variables to config fields.
- **Alternatives**: Standard `os.environ` (prone to runtime type errors, lacks validation).

### 3. Database Driver: Motor (Async MongoDB Driver)
- **Choice**: Motor
- **Rationale**: Official asynchronous MongoDB driver for Python. Avoids blocking the FastAPI async event loop during database calls.
- **Alternatives**: PyMongo (blocking/synchronous), Beanie ODM (adds unnecessary ODM complexity for initial setup; standard Motor is cleaner for simple health checks and direct query needs at this phase).

### 4. Frontend Tooling: Vite + Tailwind CSS
- **Choice**: React initialized with Vite, styled with Tailwind CSS.
- **Rationale**: Fast hot-module replacement (HMR), lightweight build setup compared to Create React App, and utility-first styling for premium design aesthetics.
- **Alternatives**: Next.js (not required as it is a client-side app, and project map specifies a React client).

## Risks / Trade-offs

- **[Risk]** MongoDB instance unavailable during startup or health check.
  - *Mitigation*: The connection should handle connection failures gracefully, returning `db_connected: false` in the health check rather than crashing the backend.
- **[Risk]** CORS blocking requests from React client to FastAPI server.
  - *Mitigation*: Enable standard CORS middleware in FastAPI from the start.
