## Why

This change implements Phase 7 of the development cycle: the Report/Export Agent. It allows users to compile their job search results and detailed analyses (including skill gap scores and cached interview questions) into standard downloadable formats (Excel and PDF). This enables users to save, share, and review their job opportunities offline.

## What Changes

- **Report/Export Agent/Service**:
  - Implement a purely Python-based `ExportAgent` / `ExportService` in `backend/agents/export_agent.py` (no LLM needed).
  - Fetches the specified list of `job_ids` from MongoDB.
  - Safely extracts fields like `company`, `role`, `location`, `salary`, `apply_link`, and cached analysis details (`skill_match_score`, `matched_skills`, `missing_skills`). Handle missing optional fields gracefully without crashing.
- **Excel Export**:
  - Compile the list of jobs into a spreadsheet using `openpyxl`.
  - Include columns: Company, Role, Location, Salary, Relevance Score (in-memory matching if available, else omitted), Skill Match Score, Matched Skills, Missing Skills, Apply Link.
- **PDF Export**:
  - Compile the jobs into a clean, well-formatted document using `reportlab`.
  - Display one clear section per job, optimized for readability (not a raw database table dump).
- **File Serving & Endpoint**:
  - Mount a static files handler in `backend/main.py` (`/static/exports`) to serve files generated in a local exports folder.
  - Implement a `POST /api/v1/export` endpoint.
  - Accepts a JSON body: `{ "job_ids": ["..."], "format": "excel" | "pdf" }`.
  - Generates the requested file, saves it to the static exports directory, and returns a JSON response containing `file_url`, `format`, and `job_count` matching the `api.md` spec.

## Capabilities

### New Capabilities
- `export-generation`: Ability to fetch selected job documents from MongoDB and compile them into clean, structured Excel (.xlsx) and PDF (.pdf) reports served via a static URL.

## Impact

- `backend/main.py`: Mounts `StaticFiles` at `/static` pointing to `backend/static`.
- `backend/agents/export_agent.py`: Houses Excel/PDF report generation logic.
- `backend/api/v1/export.py`: Defines the `POST /export` router and request/response schemas.
- `backend/api/v1/router.py`: Includes the new export router.
- `backend/tests/`: Adds new test coverage verifying report content generation and endpoint handling.
