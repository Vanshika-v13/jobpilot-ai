## Context

Phase 7 introduces the Report/Export Agent. Unlike previous agent phases, this is a compilation/formatting task requiring pure Python logic, without any LLM invocations or prompts. It compiles existing job listing data and cached deep analysis details into Excel or PDF formats.

## Goals / Non-Goals

**Goals:**
- Provide a `POST /api/v1/export` endpoint that complies with the schema defined in `api.md`.
- Export selected job details (company, role, location, salary, apply link, skill match score, matched/missing skills) to Excel (.xlsx).
- Export the same details to a beautifully structured, readable PDF.
- Serve generated files securely via static URL paths.
- Handle missing jobs or missing analysis fields gracefully without crashing.

**Non-Goals:**
- Implementing any frontend integration (React interface updates).
- Triggering any on-demand LLM reasoning or analysis during export (only compile what is already scraped or analyzed).
- Adding custom styling configurations via the API (use predefined default templates).

## Decisions

- **Architecture Pattern**: Define the logic in `backend/agents/export_agent.py` to align with the "Report / Export Agent" taxonomy in `docs/agents.md`.
- **File Storage & Serving**:
  - Mount FastAPI's `StaticFiles` to serve `backend/static/` at the `/static` URL path.
  - Write temporary output files under `backend/static/exports/` (add this folder to `.gitignore`).
  - Name files deterministically using a hash (e.g., MD5 or SHA-256) of the sorted list of `job_ids` combined with the requested `format` (e.g., `<hash>.xlsx` and `<hash>.pdf`). This ensures that identical export requests reuse/overwrite the same file, avoiding unbounded disk growth from repeated identical requests.
- **API Response**: Return `file_url` as an absolute URL (e.g. `http://localhost:8000/static/exports/<hash>.xlsx`) along with the requested `format` and the integer `job_count` of successfully exported listings.
- **Excel Strategy**: Use `openpyxl`. Create a styled header row with bold text, light blue fill background, and borders. Apply auto-adjusting column widths based on maximum text length.
- **PDF Strategy**: Use `reportlab.platypus` (SimpleDocTemplate, Paragraph, Table, Spacer, KeepTogether, PageBreak) to build a professional multi-page document. Each job listing is printed as a distinct block/page/section, styled with standard headings and clear tables for skills, rather than an unreadable database dump.
- **Graceful Fallback**: If a job lacks `skill_match_score`, `matched_skills`, or other analysis fields, default them to placeholder values (e.g., "Not analyzed yet", "N/A") rather than failing the export.

## Risks / Trade-offs

- **Risk**: Export folder growing indefinitely and occupying disk space.
  - *Mitigation*: The deterministic hashing strategy mitigates repeated exports of the exact same job listings. For a production environment, a periodic cron job/worker task should be added to prune older files (e.g. older than 24 hours), which is documented as a future enhancement.
- **Risk**: Local file system read/write errors.
  - *Mitigation*: Wrap the export file writing in try-except blocks and return HTTP 500 error responses with helpful error logs.
