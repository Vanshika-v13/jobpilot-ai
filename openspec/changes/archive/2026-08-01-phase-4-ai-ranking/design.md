## Context

Phases 1–3 established the runnable backend, two Playwright scrapers (Internshala, Unstop), and the Extraction Agent that normalizes raw scrape output into the `jobs` schema. All 14 tests pass. Phase 4 completes the first fully user-facing search pipeline: a single `POST /search` call that runs the LangGraph orchestration, returns a scored and sorted job list, and reads from a `user_profiles` document to personalize ranking.

The frontend is not yet active, so every capability built in this phase is backend-only and verified through tests + manual curl/Postman calls.

---

## Goals / Non-Goals

**Goals:**
- Build the **Planner Agent** — converts user search input into per-portal search plan objects.
- Build the **Ranking Agent** — scores each job 0–100 against a `user_profiles` document; produces an explanation per job.
- Wire the full **LangGraph pipeline**: Planner → Scrapers → Extraction Agent → Ranking Agent.
- Implement `POST /api/v1/search` — the real user-facing search endpoint that drives the pipeline end-to-end.
- Create the `user_profiles` collection in MongoDB with basic CRUD (`POST /api/v1/profiles`, `GET /api/v1/profiles/{id}`) to seed test data without auth.
- Write integration tests covering the happy path and key edge cases.

**Non-Goals:**
- Any frontend changes (`frontend/` is untouched).
- Changes to `backend/tools/` (scrapers are complete and passing).
- Authentication / JWT (deferred to Phase 7.5); `user_id` is accepted as a plain body field for now.
- Persisting `relevance_score` to the `jobs` collection (score is in-memory only; `skill_match_score` in the `jobs` collection remains the domain of the JD Analysis Agent in Phase 5).
- Streaming or async job delivery (synchronous response for V1).

---

## Decisions

### 1. Planner Agent — Rule-Based, Not LLM-Driven

**Choice:** Pure Python logic (no LLM call in the planner for V1).

**Rationale:** The planner's job in Phase 4 is mechanical: map `source` → list of portals, pass through `role`, `location`, `experience`, `skills` as search parameters. There is no ambiguity that requires LLM reasoning. Calling Ollama here would add 2–5 s of latency with zero accuracy benefit.

**Future path:** If multi-intent parsing or complex query rewriting is needed, the planner node can be upgraded to an LLM call without changing the graph interface.

**Alternatives:** LangChain function-calling planner (premature; adds latency and complexity for no gain at this stage).

---

### 2. Ranking Agent — Hybrid Scoring (No Embeddings in V1)

**Choice:** Hybrid = rule-based signals (70%) + LLM explanation (30% qualitative, not numeric).

The score is computed entirely in Python:

| Signal | Weight | Method |
|---|---|---|
| Skill overlap | 40 pts | `len(job_skills ∩ user_skills) / len(job_skills)` × 40 |
| Experience match | 20 pts | Parse ranges; full points if user years ∈ [min, max] |
| Location match | 20 pts | Exact string match or "Remote"; partial if same city |
| Role alignment | 20 pts | Token overlap between `role` and `preferred_roles` |

The LLM (Ollama) generates a **1–2 sentence explanation** using `prompts/ranking-agent.md` — it does not produce the numeric score. This keeps the score deterministic, fast, and auditable, while still providing a human-readable rationale.

**Why not embeddings?** Embedding-based similarity (e.g. sentence-transformers cosine similarity) adds a model download requirement and cold-start latency. It is the correct upgrade path once the codebase is stable (Phase 5+), but not needed for a working V1 ranker.

**Alternatives considered:**
- Pure LLM scoring: Non-deterministic, slow (one LLM call per job × N jobs), hard to debug.
- Pure rule-based (no LLM): Fast but produces no user-facing explanation. Rejected because the explanation is a UX requirement per `docs/agents.md`.

---

### 3. LangGraph Orchestration — Linear Pipeline, No Branching

**Choice:** A single `StateGraph` with nodes `planner → scrape_internshala → scrape_unstop → extract → rank`. Source-conditional scraping (skip nodes not in the plan) is handled via conditional edges on the `source` field.

**Rationale:** LangGraph's `StateGraph` is the architecture documented in `docs/architecture.md`. Keeping Phase 4 as a linear pipeline avoids complexity (no parallel fan-out, no retry loops) while correctly wiring all existing agents into the graph.

**Tradeoff:** Running Internshala and Unstop sequentially is slower than parallel. Parallelism can be added via LangGraph's `Send` primitive in a follow-up without touching the node definitions.

---

### 4. `user_profiles` CRUD — No Auth, Minimal Surface

**Choice:** `POST /api/v1/profiles` (create) + `GET /api/v1/profiles/{id}` (fetch). No update/delete in Phase 4.

**Rationale:** Phase 7.5 introduces full auth. For now, `POST /search` accepts `profile_id` as a body field so agents can look up the profile. This avoids blocking Phase 4 on auth infrastructure while keeping the DB shape correct per `docs/database.md`.

**Important:** The `user_id` field in `user_profiles` is stored but not validated against a `users` document (no FK constraint in MongoDB). This will be enforced when auth is wired in Phase 7.5.

---

### 5. `relevance_score` is In-Memory Only

This is a hard constraint from `docs/agents.md`:

> *"The ranking is done in-memory — scores are not persisted to the `jobs` collection."*

The `POST /search` response includes `relevance_score` and `explanation` per job. Neither field is written to MongoDB. The jobs returned in the search response are freshly scraped or fetched from existing records in the `jobs` collection; the ranking layer annotates them in memory before returning.

`skill_match_score` (written to `jobs` collection) remains the JD Analysis Agent's domain (Phase 5).

---

## Risks / Trade-offs

- **[Risk]** Ollama unavailable at ranking time: explanation generation fails.
  - *Mitigation:* Catch `OllamaException`; fall back to a template explanation string. Score is still returned.
- **[Risk]** Scraper returns 0 results (portal changes, rate limiting): Ranking Agent receives empty list.
  - *Mitigation:* Return `{"jobs": [], "message": "No results found"}` with HTTP 200. Do not error.
- **[Risk]** Large result sets (50+ jobs) make the LLM explanation loop slow.
  - *Mitigation:* Cap explanation generation at top-N jobs (e.g. 20) by score before sending to LLM. Document this cap.
- **[Risk]** `experience_required` field from scrapers may be inconsistently formatted.
  - *Mitigation:* Parser in the ranking agent handles `"0-2 years"`, `"Fresher"`, `"NA"` patterns. Falls back to 0 pts if unparseable.
