# AI Agents

> Field definitions: [database.md](./database.md) · Endpoint contracts: [api.md](./api.md)
> This file describes agent responsibilities and data flow — not code.

---

## 1. Planner Agent

**Purpose:** Converts search form input into a structured, multi-portal search plan that the scraping layer can execute.

**Input:** `role`, `location`, `experience`, `skills`, `source` (from `POST /search`)

**Output:** List of portal-specific search plans, each containing: target URL, search parameters, pagination strategy.

**Tools / Model:** LangChain + Ollama (local LLM)

**Notes:** The planner decides which portals to hit (Internshala, Wellfound, Unstop) and how to translate user intent into portal-specific query formats. If `source` is `"all"`, it generates plans for every supported portal.

---

## 2. Extraction Agent

**Purpose:** Converts raw scraped HTML/JSON from any portal into the standardized `jobs` schema defined in [database.md](./database.md).

**Input:** Raw page content (HTML or JSON) + source portal name.

**Output:** One or more `jobs` documents matching the collection shape in database.md.

**Tools / Model:** LangChain + Ollama for unstructured extraction; Playwright provides the raw content.

**Notes:** Each portal returns data in a different format. This agent normalizes all of them into one consistent shape. It must populate `required_skills` and `preferred_skills` even when the portal doesn't separate them — the LLM infers the split from `raw_description`.

**Unstop Structured Data Path:** Unstop's scraper (`backend/tools/unstop.py`) returns pre-structured JSON from Unstop's public API instead of raw HTML. Each Unstop result includes a `"structured": True` flag along with already-extracted top-level fields: `title`, `company`, `location`, `salary`, `skills`, and `description`. The Extraction Agent should detect this flag and, when present, apply direct field mapping to the `jobs` schema — **no LLM parsing call is needed** for Unstop listings. This saves one LLM invocation per Unstop result. Internshala and Wellfound results continue to carry `raw_html` with actual HTML content and require full LLM-based extraction.

---

## 3. Ranking Agent

**Purpose:** Scores each job 0–100% against the user's profile and generates a short explanation for the score.

**Input:** List of `jobs` documents + `user_profiles` document for the current user.

**Output:** Each job annotated with: `relevance_score` (0–100), `explanation` (1–2 sentences).

**Tools / Model:** LangChain + Ollama

**Notes:** Scoring factors include skill overlap, experience fit, location preference, and role alignment. Jobs are returned sorted by score descending. The ranking is done in-memory — scores are not persisted to the `jobs` collection. `relevance_score` represents list-view ranking (in-memory, not persisted), whereas `skill_match_score` represents detail-view deep analysis (persisted to jobs collection, cached after first computation).

---

## 4. JD Analysis Agent

**Purpose:** Deep-analyzes a single job description to extract structured insights and identify skill gaps relative to the user's profile.

**Input:** `job_id` (resolves to a `jobs` document) + `user_id` (resolves to a `user_profiles` document). Triggered by `POST /jobs/{id}/analyze`.

**Output:** `matched_skills`, `missing_skills`, `skill_match_score`, `summary` (as defined in api.md).

**Tools / Model:** LangChain + Ollama

**Topic Details:**
- **Matched Skills:** Skills present in both the job's `required_skills`/`preferred_skills` and the user's `skills`.
- **Missing Skills:** Skills the job requires that the user does not have.
- **Learning Priority:** Missing skills ordered by importance (required before preferred, frequency in market demand).

**Notes:** The analysis uses the `raw_description` for nuance beyond the extracted skill lists. The summary should be actionable — e.g. "Strong match. Consider learning Docker to close the main gap." The results (`skill_match_score`, `matched_skills`, `missing_skills`, `learning_priority`, and `jd_summary` as `summary`) are persisted to the jobs collection and cached.

---

## 5. Interview Agent

**Purpose:** Generates role-specific interview questions from a job description, covering both technical and HR topics.

**Input:** `job_id` + `user_id` + `question_count`. Triggered by `POST /jobs/{id}/interview-questions`.

**Output:** `questions[]` — each with `question`, `topic`, `difficulty` (as defined in api.md).

**Tools / Model:** LangChain + Ollama

**Notes:** Questions are split roughly 70% technical / 30% HR-behavioral. Technical questions are derived from `required_skills` and `raw_description`. Difficulty levels: `easy`, `medium`, `hard`. Questions should be specific to the role, not generic.

---

## 6. Report / Export Agent

**Purpose:** Compiles ranked jobs and analysis results into a downloadable Excel or PDF file.

**Input:** `job_ids[]` + `format`. Triggered by `POST /export`.

**Output:** `file_url` pointing to the generated file.

**Tools / Model:** Python libraries (openpyxl for Excel, reportlab or similar for PDF). No LLM needed.

**Notes:** The export includes: job details, match scores, and skill-gap summaries (if analysis was run). This is a utility agent — it formats data, it does not generate new insights.
