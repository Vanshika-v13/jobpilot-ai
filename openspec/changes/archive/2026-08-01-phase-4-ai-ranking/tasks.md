## 1. Schemas & Data Layer

- [x] 1.1 Create `backend/schemas/search.py` — define `SearchRequest`, `RankedJob` (job fields + `relevance_score: int` + `explanation: str`), and `SearchResponse` Pydantic models.
- [x] 1.2 Create `backend/schemas/profile.py` — define `UserProfileCreate` and `UserProfileResponse` Pydantic models matching the `user_profiles` schema in `docs/database.md`.
- [x] 1.3 Create `backend/database/user_profiles.py` — implement `insert_profile(profile: dict) -> str` and `get_profile_by_id(profile_id: str) -> dict | None` using the Motor async client.

---

## 2. Planner Agent

- [x] 2.1 Create `backend/agents/planner_agent.py`:
  - Define a `SearchPlan` dataclass/TypedDict: `{ portal: str, role: str, location: str, experience: str, skills: list[str] }`.
  - Implement `create_search_plans(role, location, experience, skills, source="all") -> list[SearchPlan]`.
  - If `source="internshala"` → one plan for Internshala only.
  - If `source="unstop"` → one plan for Unstop only.
  - If `source="all"` → two plans, one per portal.
  - No LLM call; pure Python logic.
- [x] 2.2 Update `prompts/planner.md` — document the Planner's input/output contract and behavior (for reference; not used in code for V1).

---

## 3. Ranking Agent

- [x] 3.1 Create `backend/prompts/ranking_prompt.py` — define `RANKING_PROMPT` constant used when asking Ollama for job explanation text. Prompt must accept `job_role`, `job_skills`, `user_skills`, `score`, and instruct the LLM to produce a 1–2 sentence explanation only.
- [x] 3.2 Update `prompts/ranking-agent.md` — fill in the stub with the full system prompt and expected output format.
- [x] 3.3 Create `backend/agents/ranking_agent.py`:
  - Implement `normalize_skill(s: str) -> str` helper:
    - Lowercase and strip whitespace from the input string.
    - Collapse internal whitespace runs to a single space.
    - Resolve common aliases/synonyms to a canonical form via a `_SKILL_ALIASES` dict (e.g. `"react.js"` → `"react"`, `"reactjs"` → `"react"`, `"js"` → `"javascript"`, `"node.js"` → `"nodejs"`, `"ts"` → `"typescript"`, `"scss"` → `"sass"`).
    - Unknown skills are returned as-is (lowercased) — full fuzzy matching is a future enhancement.
  - Implement `compute_score(job: dict, profile: dict) -> int`:
    - **Before computing intersection**, normalise both `job_skills` and `user_skills` with `normalize_skill`.
    - Skill overlap: `min(len(norm_job ∩ norm_user) / max(len(norm_job), 1) * 40, 40)` → 0–40 pts.
    - Experience match: parse `experience_required` (handles `"0-2 years"`, `"Fresher"`, `"NA"`); 20 pts if user's `experience_years` ∈ range, 10 pts if within 1 yr of range.
    - Location match: 20 pts for exact city/Remote match; 10 pts for same state; 0 otherwise.
    - Role alignment: token overlap between `job.role` and `profile.preferred_roles`; 20 pts if ≥1 token matches.
  - Implement `generate_explanation(job: dict, profile: dict, score: int) -> str` — calls `get_llm()` with `RANKING_PROMPT`; catches `Exception` and returns a fallback string if Ollama is unavailable.
  - Implement `rank_jobs(jobs: list[dict], profile: dict) -> list[dict]` — annotates each job with `relevance_score` and `explanation`, sorts descending by score, caps explanation generation at top 20 jobs.
  - Scores are **not** written to MongoDB.

---

## 4. LangGraph Pipeline

- [x] 4.1 Create `backend/agents/graph.py`:
  - Define `SearchState` (TypedDict) with the following fields:
    - `plans: list[SearchPlan]`
    - `raw_jobs: Annotated[list, operator.add]` — **must use a LangGraph reducer**. Declare as `from typing import Annotated` + `import operator` and annotate the field so LangGraph appends node outputs rather than overwriting. Without this, when `source="all"` runs both scraper nodes, whichever runs last silently overwrites the other's results.
    - `extracted_jobs: list[dict]`
    - `ranked_jobs: list[dict]`
    - `profile: dict`
    - `search_id: str`
  - Implement nodes: `planner_node`, `scrape_internshala_node`, `scrape_unstop_node`, `extract_node`, `rank_node`.
  - Wire graph: `planner_node → route_scrapers → [scrape_internshala_node, scrape_unstop_node] → extract_node → rank_node`.
  - `route_scrapers` is a conditional edge that reads `state["plans"]` and routes to the correct scraper node(s). If `source="all"`, chain both scraper nodes.
  - Compile the graph and export `search_graph = graph.compile()`.

---

## 5. User Profiles API

- [x] 5.1 Create `backend/api/v1/profiles.py`:
  - `POST /api/v1/profiles` — validates `UserProfileCreate`, calls `insert_profile()`, returns `UserProfileResponse` with generated `_id`.
  - `GET /api/v1/profiles/{id}` — calls `get_profile_by_id()`, returns `UserProfileResponse` or 404.
- [x] 5.2 Register `profiles` router in `backend/api/v1/__init__.py` and `backend/main.py`.

---

## 6. Search Endpoint

- [x] 6.1 Create `backend/api/v1/search.py`:
  - `POST /api/v1/search` — validates `SearchRequest` (`role`, `location`, `experience`, `skills`, `source="all"`, `profile_id`).
  - Fetches profile from MongoDB via `get_profile_by_id(profile_id)`; returns 404 if not found.
  - Creates `job_searches` record (status `"running"`) before invoking the graph.
  - Invokes `search_graph.invoke(state)` with the assembled `SearchState`.
  - Updates `job_searches` record to `"completed"` with `job_count`.
  - Returns `SearchResponse`: `{ search_id, jobs: [RankedJob], total }`.
- [x] 6.2 Register `search` router in `backend/api/v1/__init__.py` and `backend/main.py`.

---

## 7. Tests

- [x] 7.1 Create `backend/tests/test_planner_agent.py`:
  - Test `source="internshala"` → 1 plan with portal = "internshala".
  - Test `source="unstop"` → 1 plan with portal = "unstop".
  - Test `source="all"` → 2 plans, one per portal.
  - Test all fields (`role`, `location`, `experience`, `skills`) are passed through correctly.
- [x] 7.2 Create `backend/tests/test_ranking_agent.py`:
  - Test `normalize_skill` lowercases and strips whitespace.
  - Test `normalize_skill("React.js") == normalize_skill("React")` (alias normalisation).
  - Test `normalize_skill("JS") == "javascript"` and `normalize_skill("TS") == "typescript"`.
  - Test `normalize_skill` for an unknown skill returns it lowercased (no alias).
  - Test `compute_score` with perfect skill match → 40 pts for skill component.
  - Test `compute_score` with zero skill overlap → 0 pts for skill component.
  - **Test `compute_score` where job lists `"React.js"` and profile lists `"React"` → full skill score (normalization regression).**
  - Test experience parser for `"0-2 years"`, `"Fresher"`, `"NA"`.
  - Test location match: exact, "Remote", no match.
  - Test `rank_jobs` output is sorted descending by `relevance_score`.
  - Test `rank_jobs` with empty job list → returns `[]`.
- [x] 7.3 Create `backend/tests/test_profiles.py`:
  - Test `POST /api/v1/profiles` creates a document and returns an `id`.
  - Test `GET /api/v1/profiles/{id}` retrieves the created document.
  - Test `GET /api/v1/profiles/{invalid_id}` returns 404.
- [x] 7.4 Create `backend/tests/test_search_endpoint.py`:
  - Mock scrapers to return a fixed list of raw jobs.
  - Test `POST /api/v1/search` with a seeded profile returns a ranked list sorted by `relevance_score`.
  - Test `POST /api/v1/search` with `source="internshala"` only calls the Internshala scraper mock.
  - Test `POST /api/v1/search` with invalid `profile_id` returns 404.
  - **Dual-source accumulation test** (`source="all"` reducer guard):
    - Mock `scrape_internshala_node` to return `[{"source": "internshala", ...}]` and `scrape_unstop_node` to return `[{"source": "unstop", ...}]` — each with at least one distinct job.
    - Call `POST /api/v1/search` with `source="all"`.
    - Assert the response `jobs` list contains entries from **both** sources (i.e. at least one job with `source == "internshala"` AND at least one with `source == "unstop"`).
    - This test will fail if `raw_jobs` is a plain `list` instead of `Annotated[list, operator.add]`, making the regression detectable at the test layer.

---

## 8. Verification & Wrap-Up

- [x] 8.1 Run `pytest` from `backend/` — all tests pass (target: ≥25 passing).
- [x] 8.2 Manual smoke test: seed a profile via `POST /api/v1/profiles`, then call `POST /api/v1/search` with `source="all"` and verify returned jobs have `relevance_score` and `explanation` populated.
- [x] 8.3 Update `docs/phases.md` current phase marker to **Phase 4 (complete)**.
- [x] 8.4 Commit: `"Phase 4 complete: Planner + Ranking agents, LangGraph pipeline, POST /search, user_profiles CRUD"`.
