# Architecture

> Details: [database.md](./database.md) · [api.md](./api.md) · [agents.md](./agents.md)

---

## System Overview

```
┌──────────┐     HTTP      ┌──────────────────────────────────────┐      ┌─────────┐
│ Frontend │ ──────────▶   │            Backend (FastAPI)          │ ───▶ │ MongoDB │
│ React    │   ◀──────────  │                                      │ ◀─── │         │
└──────────┘    JSON        │  api/ → services/ → agents/ → tools/ │      └─────────┘
                            └────────────┬─────────────────────────┘
                                         │
                              ┌──────────▼──────────┐
                              │   LangGraph + LLM   │
                              │  (Ollama / Gemini)   │
                              └──────────┬──────────┘
                                         │
                              ┌──────────▼──────────┐
                              │    Playwright        │
                              │  (portal scrapers)   │
                              └─────────────────────┘
```

---

## Frontend Architecture

- **React + Vite + Tailwind CSS** — single-page app, no SSR.
- **List View:** Displays ranked job cards (role, company, score). Cheap to render — data comes pre-ranked from the search endpoint.
- **Detail View:** Opens on click. Triggers on-demand analysis (JD analysis, skill gap, interview questions). Heavy agents run only here, never on the full list.

---

## Backend Architecture

FastAPI server, organized by responsibility:

- `api/` — Route handlers. Thin layer — validates input, calls services, returns JSON.
- `services/` — Business logic. Orchestrates agent calls, manages search lifecycle.
- `agents/` — LangChain/LangGraph agent definitions (one file per agent, see [agents.md](./agents.md)).
- `tools/` — Playwright scrapers and LangChain tool wrappers.
- `database/` — MongoDB connection and collection access via Motor (async driver).
- `core/` — Config, settings, middleware.

---

## AI Architecture

- **Orchestration:** LangGraph manages multi-step agent workflows (plan → scrape → extract → rank).
- **LLM provider:** Controlled by a single config variable (`LLM_PROVIDER`).
  - `ollama` (default) — local, free, no API key needed.
  - `gemini` (fallback) — cloud, used when Ollama is unavailable or for higher-quality analysis.
- **All agents use the same provider switch** — no agent is hardcoded to a specific LLM.

---

## Browser Automation Flow

- One scraper module per portal (`internshala.py`, `wellfound.py`, `unstop.py`).
- Each scraper uses Playwright to navigate, paginate, and extract raw HTML/JSON.
- Raw content is passed to the Extraction Agent, which normalizes it into the `jobs` schema from [database.md](./database.md).
- Adding a new portal = one new scraper file + no changes to downstream agents.

---

## Data Flow

### List View (search) — cheap path

```
User input → Planner Agent → Playwright scrapers → Extraction Agent → Ranking Agent → ranked job list
```

All jobs are scraped, normalized, and scored in one pipeline. No per-job LLM calls beyond ranking.

### Detail View (click) — on-demand path

```
User clicks a job → JD Analysis Agent (skill gap) → stored for that job
                   → Interview Agent (questions)  → returned on request
```

Heavy analysis runs only when the user selects a specific job. This keeps the list view fast and the LLM cost proportional to user interest, not search volume.
