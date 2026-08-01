## Why

Phase 2 delivered two working scrapers — Internshala (Playwright/HTML) and Unstop (public JSON API) — but their raw output cannot be stored or consumed downstream. The Internshala scraper returns `raw_html` blobs that need LLM-based extraction; the Unstop scraper returns pre-structured JSON that only needs field mapping. Without a normalization step and database persistence, there is no way to link scraped results back to a user's search or feed them into the Ranking Agent in Phase 4.

Phase 3 closes this gap by building the Extraction Agent and a thin database access layer, turning raw scraper output into standard `jobs` documents in MongoDB and creating the `job_searches` record that links everything back to the triggering search.

## What Changes

- **New `backend/agents/extraction_agent.py`** — Accepts a list of raw scraper results (mixed Internshala and Unstop) plus search metadata. For each result:
  - If `structured: True` (Unstop): maps pre-extracted fields directly to the `jobs` schema — no LLM call.
  - If `raw_html` is present (Internshala): sends the HTML to Ollama/Gemini via LangChain to extract structured job fields.
  - Writes every normalized job to the `jobs` collection and returns the inserted documents.
- **New `backend/database/collections.py`** — Typed helper functions for `jobs` and `job_searches` collections (insert, query, update status) using Motor.
- **New `backend/tests/test_extraction_agent.py`** — Unit tests covering both extraction paths (structured + HTML), field validation against the `jobs` schema, and the `job_searches` lifecycle.
- **New `backend/tests/fixtures/unstop_structured_sample.json`** — Sample Unstop scraper output for deterministic testing.
- **Updated `backend/requirements.txt`** — Adds `langchain`, `langchain-community` (Ollama integration).
- **Updated `backend/core/config.py`** — Adds `ollama_base_url` setting (default `http://localhost:11434`).

## Capabilities

### New Capabilities
- `extraction-agent`: Normalizes raw scraper output (HTML or structured JSON) into the standardized `jobs` schema from database.md, supporting both LLM-based and direct-mapping paths.
- `job-persistence`: Inserts normalized job documents into the `jobs` MongoDB collection via Motor.
- `search-lifecycle`: Creates and updates `job_searches` records to link results back to the triggering search, including status transitions (`pending` → `running` → `completed`/`failed`) and `job_count`.

### Modified Capabilities
- `env-config`: Extended with `ollama_base_url` for LLM connectivity.

## Impact

- **New dependencies:** `langchain>=0.2.0`, `langchain-community>=0.2.0` (Ollama ChatModel wrapper).
- **New files:** `backend/agents/extraction_agent.py`, `backend/database/collections.py`, `backend/tests/test_extraction_agent.py`, `backend/tests/fixtures/unstop_structured_sample.json`.
- **Modified files:** `backend/requirements.txt`, `backend/core/config.py`, `backend/agents/__init__.py`.
- **No new API endpoints** — extraction is an internal pipeline step, not user-facing. API routes come in Phase 4.
- **No breaking changes** — additive only; existing Phase 1/2 code untouched.
- **Valid `source` values** are `internshala` and `unstop` only (Wellfound excluded from V1).
