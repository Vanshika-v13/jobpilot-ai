## Context

Phase 5 introduces the **JD Analysis Agent** and the accompanying `POST /api/v1/jobs/{id}/analyze` endpoint. In previous phases, jobs were scraped and given a preliminary ranking in memory. When the user views a job's details, they require a deep-dive analysis of that job description, identifying specific skill gaps and learning priorities compared to their profile. 

This phase is entirely backend-focused. The frontend remains inactive.

---

## Goals / Non-Goals

**Goals:**
- Implement **JD Analysis Agent** in `backend/agents/jd_analysis_agent.py`.
- Support extraction of `required_skills`, `preferred_skills`, `experience_required`, `responsibilities`, `important_keywords`, and `jd_summary` using the existing `get_llm()` factory.
- Implement **Skill Gap logic** inside the agent, reusing the `normalize_skill()` helper from `ranking_agent.py` to ensure consistent alias resolution.
- Cache analysis results to the MongoDB `jobs` collection (fields: `skill_match_score`, `matched_skills`, `missing_skills`, `learning_priority`, `jd_summary`).
- Implement the `POST /api/v1/jobs/{id}/analyze` endpoint accepting a `profile_id` in the body and returning the analysis results.
- Implement the description safety check `sanitize_description()` prior to passing content to the LLM.
- Write unit and integration tests.

**Non-Goals:**
- Any frontend work (`frontend/` is untouched).
- Any modifications to the Playwright scraper layer in `backend/tools/`.
- User authentication (handled in Phase 7.5; endpoints will access profiles directly by ID).

---

## Decisions

### 1. Unified JD Analysis and Skill Gap Agent
- **Choice:** Both JD analysis (LLM extraction) and skill gap calculation (Python comparison) live within `backend/agents/jd_analysis_agent.py`.
- **Rationale:** A single entry point makes it simple to orchestrate. First, the LLM is called to parse the description. Then, the resulting lists of required and preferred skills are compared against the user profile using `normalize_skill` in Python to output `matched_skills`, `missing_skills`, and `learning_priority`.

### 2. Skill Match Score Formula
- **Choice:** Weighted score based on required and preferred skills:
  - **Required Skills** weight: 70%
  - **Preferred Skills** weight: 30%
  - If a job has no required skills, the score is based entirely on preferred skills. If there are no preferred skills, it's based entirely on required skills. If neither required nor preferred skills are listed/extracted, the score defaults to a fixed neutral value of `50`, not an "either/or" possibility involving an extra LLM call. This avoids triggering an additional LLM inference call, keeping behavior deterministic and eliminating extra latency or costs.
  - Formula:
    `Score = (0.7 * (matched_required / total_required) + 0.3 * (matched_preferred / total_preferred)) * 100`

### 3. Caching Strategy
- **Choice:** Read-through cache persisted directly on the `jobs` document in MongoDB.
- **Rationale:** The `jobs` collection already has fields defined for this (`skill_match_score`, `matched_skills`, etc.). By persisting them to the existing document, we avoid creating another collection. When `POST /jobs/{id}/analyze` is hit:
  1. Fetch the job document.
  2. If `skill_match_score` is already present (not null/None), return the cached fields immediately.
  3. If not cached, fetch the user profile, run the agent, update the job document in MongoDB, and return the newly calculated fields.

### 4. Input Sanitization
- **Choice:** Import and apply `sanitize_description()` from `backend/agents/extraction_agent.py`.
- **Rationale:** Prevents prompt injection or hazardous HTML from being processed by the LLM, maintaining consistency with Phase 4's extraction safety checks.

---

## Risks / Trade-offs

- **[Risk]** The job description is extremely long, leading to LLM context overflow or high latency.
  - *Mitigation:* Truncate the sanitized description to a safe token length (e.g., 4000 characters) before sending it to the LLM.
- **[Risk]** Profile does not exist.
  - *Mitigation:* Return a clear HTTP 404 error if the `profile_id` is invalid.
- **[Risk]** The LLM call in `jd_analysis_agent` fails (e.g., Ollama is unavailable, times out, or returns a malformed response).
  - *Mitigation:* The endpoint must not crash with a 500 error. Instead, handle the exception gracefully and return a partial result using whatever skills data is already available directly from the job document (e.g., `required_skills`/`preferred_skills` already in the document from Phase 3, if present) combined with a fallback `jd_summary` message: `"Detailed analysis unavailable — showing basic skill comparison."`. Do not cache this failed/partial result in the MongoDB collection; leave `skill_match_score` as `null` so that a subsequent request will retry the full analysis.
