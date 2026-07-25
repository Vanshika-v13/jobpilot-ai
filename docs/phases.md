# Development Phases

> Current phase: **Phase 1**
> Update this marker as each phase is completed.

---

## Phase 1 — Project Setup

Initialize backend app, wire up the database, and confirm everything runs.

- Initialize FastAPI application in `backend/`
- Set up MongoDB connection via Motor (async driver)
- Configure `.env` loading and `core/config.py` settings
- Implement `GET /health` endpoint (server + DB status)

---

## Phase 2 — Browser Automation

Build Playwright scrapers that can pull raw job data from each portal.

- Create scraper module for Internshala
- Create scraper module for Wellfound
- Create scraper module for Unstop
- Each scraper outputs raw HTML/JSON per listing — no normalization yet

---

## Phase 3 — Job Extraction & Storage

Normalize scraped data into the standard job schema and persist it.

- Build the Extraction Agent (raw content → `jobs` schema from [database.md](./database.md))
- Save normalized jobs to the `jobs` collection in MongoDB
- Create the `job_searches` record to link results back to a search
- Verify all fields populate correctly across all three portals

---

## Phase 4 — AI Ranking

Add the Planner and Ranking agents so `/search` returns a scored job list.

- Build the Planner Agent (user input → per-portal search plans)
- Build the Ranking Agent (jobs + user profile → scored + sorted list)
- Implement `POST /search` endpoint end-to-end
- Create `user_profiles` collection and seed test data
- Full pipeline works: search → plan → scrape → extract → rank → respond

---

## Phase 5 — JD Analysis & Skill Gap

Deep-analyze a single job on demand with skill-gap comparison.

- Build the JD Analysis Agent (extract skills, experience, responsibilities, keywords)
- Add Skill Gap Analysis logic (matched skills, missing skills, learning priority)
- Implement `POST /jobs/{id}/analyze` endpoint
- Return actionable summary referencing the user's profile

---

## Phase 6 — Interview Question Generation

Generate role-specific interview questions for a selected job.

- Build the Interview Agent (job description → technical + HR questions)
- Implement `POST /jobs/{id}/interview-questions` endpoint
- Questions tagged with `topic` and `difficulty`
- 70/30 split between technical and behavioral questions

---

## Phase 7 — Export

Allow users to export job results and analysis to a file.

- Build the Report/Export Agent (compile ranked jobs + analysis data)
- Implement `POST /export` endpoint
- Support Excel output (openpyxl)
- Support PDF output (reportlab or equivalent)

---

## Phase 8 — Frontend Integration & Polish

Initialize React + Vite + Tailwind CSS and connect all backend endpoints to the React UI.

- Initialize React + Vite + Tailwind CSS in `frontend/` (done fresh here per user's own design preference)
- Build the search form and list view (displays ranked job cards)
- Build the detail view (triggers JD analysis + interview questions on click)
- Wire up export functionality
- Responsive layout, loading states, error handling
- End-to-end user flow testing
