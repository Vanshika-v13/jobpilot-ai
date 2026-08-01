## Why

Phases 1–3 delivered a fully automated scraping and extraction pipeline. Jobs are being pulled from Internshala and Unstop, normalized into the `jobs` schema, and persisted in MongoDB. However, the pipeline has no entry point for an actual user and no intelligence to prioritize results. Phase 4 changes that: it adds the two remaining agents (Planner, Ranking), wires them into a LangGraph graph, surfaces a real `POST /search` endpoint, and introduces the `user_profiles` collection that powers personalized ranking — all without touching the frontend or the existing scraper layer.

---

## What Changes

### New Files

- **`backend/agents/planner_agent.py`** — Planner Agent. Pure Python (no LLM). Takes `role`, `location`, `experience`, `skills`, `source` and returns a list of `SearchPlan` objects (one per target portal). If `source="all"`, plans are generated for both Internshala and Unstop.

- **`backend/agents/ranking_agent.py`** — Ranking Agent. Scores each job 0–100 using a hybrid approach: rule-based numeric signals (skill overlap 40 pts, experience match 20 pts, location match 20 pts, role alignment 20 pts) + LLM-generated 1–2 sentence explanation per job (Ollama via `get_llm()`). Score is computed in Python; LLM is only called for the explanation text. `relevance_score` is **not** persisted to MongoDB.

- **`backend/agents/graph.py`** — LangGraph `StateGraph` that wires `planner → scrape_internshala → scrape_unstop → extract → rank` as a connected pipeline. Conditional edges route around scraper nodes not present in the plan (e.g. `source="internshala"` skips the Unstop node).

- **`backend/api/v1/search.py`** — `POST /api/v1/search` route. Validates the request body, invokes the LangGraph pipeline, and returns the ranked job list. Also creates the `job_searches` record in MongoDB to track the search.

- **`backend/api/v1/profiles.py`** — `POST /api/v1/profiles` (create profile) and `GET /api/v1/profiles/{id}` (fetch profile). Minimal CRUD; no auth required in Phase 4.

- **`backend/database/user_profiles.py`** — MongoDB CRUD helpers for the `user_profiles` collection (`insert_profile`, `get_profile_by_id`).

- **`backend/schemas/search.py`** — Pydantic request/response schemas for `POST /search`: `SearchRequest`, `RankedJob`, `SearchResponse`.

- **`backend/schemas/profile.py`** — Pydantic schemas for `POST /profiles` / `GET /profiles/{id}`: `UserProfileCreate`, `UserProfileResponse`.

- **`backend/prompts/ranking_prompt.py`** — Python constant `RANKING_PROMPT` used by the Ranking Agent when calling Ollama for job explanations.

- **`backend/tests/test_planner_agent.py`** — Unit tests for Planner Agent logic (correct portal selection, parameter pass-through).

- **`backend/tests/test_ranking_agent.py`** — Unit tests for Ranking Agent score computation (skill overlap math, experience parsing, location matching).

- **`backend/tests/test_search_endpoint.py`** — Integration test for `POST /search` using FastAPI `TestClient` with mocked scrapers.

- **`backend/tests/test_profiles.py`** — Integration tests for profile CRUD endpoints.

### Modified Files

- **`backend/main.py`** — Register the new `search` and `profiles` API routers.
- **`backend/api/v1/__init__.py`** — Include new route modules.
- **`prompts/ranking-agent.md`** — Fill in the Ranking Agent system prompt template (currently a stub).
- **`prompts/planner.md`** — Document the Planner's behavior (currently a stub).
- **`docs/phases.md`** — Update current phase marker from Phase 3 → Phase 4.

---

## Capabilities

### New Capabilities

- **`planner-agent`**: Converts search form input into per-portal `SearchPlan` objects. Determines which scrapers to invoke based on `source` field.
- **`ranking-agent`**: Scores and sorts jobs against a user profile using deterministic rule-based signals + LLM-generated explanation. Returns `relevance_score` (0–100) and `explanation` per job. In-memory only.
- **`langgraph-search-pipeline`**: End-to-end LangGraph pipeline: Planner → Scrapers → Extraction Agent → Ranking Agent.
- **`search-endpoint`**: `POST /api/v1/search` — accepts role, location, experience, skills, source, profile_id; returns ranked job list.
- **`user-profiles-crud`**: `POST /api/v1/profiles` and `GET /api/v1/profiles/{id}` for creating and fetching user profiles without auth.

### Modified Capabilities

- **`search-record`**: `job_searches` collection record is now created as part of the `POST /search` pipeline (was deferred in Phase 3).

---

## Impact

- **New dependencies (backend):** `langgraph` (already in requirements as a transitive dep of `langchain`; verify pinned version).
- **New files:** 12 new Python files across `agents/`, `api/v1/`, `database/`, `schemas/`, `prompts/`, and `tests/`.
- **Modified files:** `backend/main.py`, `backend/api/v1/__init__.py`, `prompts/ranking-agent.md`, `prompts/planner.md`, `docs/phases.md`.
- **APIs added:** `POST /api/v1/search`, `POST /api/v1/profiles`, `GET /api/v1/profiles/{id}`.
- **No breaking changes** — existing endpoints (`GET /health`) and scraper tools are untouched.
- **`frontend/` is not touched.**
- **`backend/tools/` is not touched.**
