## 1. Agent Logic Implementation

- [x] 1.1 Create `backend/agents/jd_analysis_agent.py` and implement the basic structure.
- [x] 1.2 Import `sanitize_description` from `backend/agents/extraction_agent.py` and implement description input sanitization.
- [x] 1.3 Implement LLM-based deep analysis using `get_llm()` to extract skills, experience, responsibilities, keywords, and summary.
- [x] 1.4 Implement skill gap logic utilizing `normalize_skill` from `ranking_agent.py` and calculate score/priorities.
- [x] 1.5 Add cached retrieval and updates to the MongoDB `jobs` collection.
- [x] 1.6 Implement LLM failure handling: if LLM extraction fails (Ollama unavailable, timeout, malformed response), return a partial result using existing job document skills (Phase 3 `required_skills`/`preferred_skills`), set fallback `jd_summary` to `"Detailed analysis unavailable — showing basic skill comparison."`, and ensure `skill_match_score` is not cached (remains `null`).

## 2. API Routes and Schemas

- [x] 2.1 Create Pydantic schemas in `backend/schemas/jobs.py` for request and response models.
- [x] 2.2 Create `backend/api/v1/jobs.py` and implement `POST /api/v1/jobs/{id}/analyze` endpoint.
- [x] 2.3 Register the new jobs router in `backend/main.py` and `backend/api/v1/__init__.py`.

## 3. Verification & Testing

- [x] 3.1 Write unit tests in `backend/tests/test_jd_analysis_agent.py` for agent logic, sanitization, skill matching math, and LLM failure fallback behavior.
- [x] 3.2 Write a unit test in `backend/tests/test_jd_analysis_agent.py` verifying that raw_description truncation (to 4000 characters) works correctly and does not break extraction.
- [x] 3.3 Write integration tests in `backend/tests/test_jd_analysis_endpoint.py` for the API endpoint, MongoDB caching behavior, and failure/partial result scenarios.
- [x] 3.4 Run the test suite to verify all tests pass.
- [x] 3.5 Update Phase marker in `docs/phases.md` to reflect Phase 5 progress.
