## 0. LLM Provider Configuration

- [x] 0.1 Add `LLM_PROVIDER` (default `"ollama"`) and `GEMINI_API_KEY` (optional) to `backend/core/config.py`.
- [x] 0.2 Create `backend/agents/llm_provider.py` with `get_llm()` factory function returning the correct LangChain chat model based on `LLM_PROVIDER`.
- [x] 0.3 Implement automatic fallback: if `LLM_PROVIDER="gemini"` and the API call fails (rate limit, quota, error), fall back to Ollama automatically with a logged warning, rather than crashing.
- [x] 0.4 If `LLM_PROVIDER="ollama"` and Ollama is unreachable, raise a clear error telling the user to run "ollama serve", not a generic timeout.
- [x] 0.5 Extraction Agent must use `get_llm()` from `llm_provider.py`, not a hardcoded provider.

## 1. Setup & Configuration

- [x] 1.1 Add `ollama_base_url` to `backend/core/config.py` with default `http://localhost:11434`.
- [x] 1.2 Add `langchain` and `langchain-community` to `backend/requirements.txt`.
- [x] 1.3 Update `.env.example` to document `OLLAMA_BASE_URL`.

## 2. Database Operations Layer

- [x] 2.1 Create `backend/database/collections.py`.
- [x] 2.2 Implement `create_job_search(search_data)` to insert a record into `job_searches` and return the `search_id`.
- [x] 2.3 Implement `update_job_search_status(search_id, status, job_count)` to handle search state transitions (`pending` -> `running` -> `completed`/`failed`).
- [x] 2.4 Implement `insert_jobs(jobs_list)` to batch insert normalized jobs into the `jobs` collection.

## 3. Extraction Agent Logic

- [x] 3.1 Create `backend/agents/extraction_agent.py`.
- [x] 3.2 Implement Pydantic schema `ExtractedJob` for LLM validation.
- [x] 3.3 Implement `extract_structured_job(raw_job)` for Unstop data (direct field mapping, no LLM call).
- [x] 3.4 Implement `extract_html_job(raw_job)` for Internshala (invoking LLM via LangChain with structured output).
- [x] 3.5 Implement main agent runner `process_scraped_results(search_id, raw_results)` that orchestrates extraction and saves results to MongoDB. Must handle per-job extraction failures gracefully (skip failed jobs, continue batch, don't crash entire search).
- [x] 3.6 Register/export `process_scraped_results` in `backend/agents/__init__.py`.

## 4. Testing & Verification

- [x] 4.1 Create `backend/tests/fixtures/unstop_structured_sample.json` containing sample structured scraper outputs.
- [x] 4.2 Create `backend/tests/test_extraction_agent.py` to unit-test direct mapping, LLM extraction (mocked), and database insertion.
- [x] 4.3 Verify MongoDB integration works with test database connection.
