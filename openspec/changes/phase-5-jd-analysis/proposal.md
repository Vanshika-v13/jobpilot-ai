## Why

Phase 4 successfully delivered the personalized job search and ranking pipeline (Planner, Ranking, and Search API). However, the ranking score is calculated from high-level extracted data. The user has no way to view a deep-dive analysis of a single job, nor can they see which specific skills they are missing compared to a job's requirements, or what they should prioritize learning. Phase 5 addresses this by building the JD Analysis Agent, which provides on-demand, deep-dive skill-gap analysis, keyword extraction, and job summaries for a single job against a user's profile, caching results directly to MongoDB.

## What Changes

- **`backend/agents/jd_analysis_agent.py`** — JD Analysis Agent. Takes a single `job_id` and `profile_id`. Fetches the job from MongoDB, checks if a cached analysis already exists. If not, normalizes the job's `raw_description` using `sanitize_description` (HTML/script sanitization) and truncates it to a maximum of 4000 characters before sending it to the LLM. Uses `get_llm()` to extract `required_skills`, `preferred_skills`, `experience_required`, `responsibilities`, and `important_keywords` from the description. If the LLM call fails, returns a partial result using the job's existing skills from the document (Phase 3) and a fallback summary, without caching the result.
- **Skill Gap Logic** — Inside `jd_analysis_agent.py`. It compares the job's skills (`required_skills` and `preferred_skills`) against the user profile's skills, using the `normalize_skill()` helper from `ranking_agent.py` for consistent, alias-aware comparison. It computes `matched_skills`, `missing_skills`, `learning_priority` (missing skills ordered by importance, e.g., required skills first, then preferred), and `skill_match_score` (0–100 score). If neither required nor preferred skills are listed/extracted, the score defaults to `50`.
- **Cache Results to MongoDB** — Persists `skill_match_score`, `matched_skills`, `missing_skills`, `learning_priority`, and `jd_summary` to the job's document in the `jobs` collection. Subsequent analyze requests retrieve the cached data directly instead of calling the LLM. If the analysis was a partial fallback due to LLM failure, caching is skipped.
- **`backend/api/v1/jobs.py`** — Registers the `POST /api/v1/jobs/{id}/analyze` endpoint. It accepts `id` as a path parameter (the job's `_id`) and `profile_id` in the request body, orchestrates the cached/new analysis flow, and returns the analysis results.
- **`backend/schemas/jobs.py`** — Pydantic schemas for the analysis request and response, including the `profile_id` payload and the detailed response structure.
- **`backend/tests/test_jd_analysis_agent.py`** — Unit tests for the JD Analysis Agent and skill-gap logic (scoring correctness, list overlap, learning priority ordering, truncation safety, and LLM failure fallback behavior).
- **`backend/tests/test_jd_analysis_endpoint.py`** — Integration tests for the `POST /api/v1/jobs/{id}/analyze` endpoint (caching behavior, database updates, error handling).

## Capabilities

### New Capabilities

- `jd-analysis`: Deep-analyzes a single job description to extract structured insights and perform skill gap analysis against a user's profile, with result caching in MongoDB.

### Modified Capabilities

None.

## Impact

- **Affected Code / APIs**: Registers a new router for job endpoints in `backend/main.py`. New API `POST /api/v1/jobs/{id}/analyze`.
- **Dependencies**: No new external dependencies. Uses existing `get_llm()`, `normalize_skill()`, and Motor helper methods.
- **No breaking changes** — Existing APIs (`POST /api/v1/search`, `GET /health`, etc.) and data shapes are preserved.
- **No frontend changes** — `frontend/` is untouched.
- **No scraper changes** — `backend/tools/` is untouched.
