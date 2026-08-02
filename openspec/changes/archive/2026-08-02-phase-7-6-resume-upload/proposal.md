## Why

This change implements Phase 7.6 of the development cycle: Resume Upload & Profile Extraction.

Currently, users must manually enter their skills, experience, and education into their profile via `POST /api/v1/profiles`. This is tedious and error-prone — most job seekers already have this information structured in their resume PDF. Phase 7.6 adds a convenience endpoint that accepts a PDF resume upload, extracts the raw text, uses the existing LLM infrastructure to parse structured profile fields (skills, experience_years, education, preferred_roles), and saves the extracted data into the authenticated user's `user_profiles` document.

This is **additive and optional** — users can still manually create/update their profile via `POST /api/v1/profiles`. The resume upload is a parallel convenience path, not a replacement.

## What Changes

- **New Endpoint**: `POST /api/v1/profile/upload-resume`
  - **Protected** by `get_current_user` (same JWT auth dependency from Phase 7.5).
  - Accepts a single PDF file via `multipart/form-data` (field name: `file`).
  - Enforces a **5 MB file size limit** — rejects uploads exceeding this threshold with HTTP 413.
  - Validates the uploaded file is a real PDF by checking **magic bytes** (`%PDF-` header), not just the filename extension or content-type header.
  - Extracts raw text from the PDF using **pdfplumber**.
  - Passes the raw text through the LLM (via `get_llm()`) using the established **PydanticOutputParser + format_instructions + retry-once + graceful-fallback** pattern (same as `extraction_agent.py`, `jd_analysis_agent.py`, `interview_agent.py`).
  - Extracts: `skills` (string[]), `experience_years` (number), `education` (string), `preferred_roles` (string[], if inferable from resume content).
  - Saves extracted data into the authenticated user's `user_profiles` document using `get_or_create_profile(user_id)` from Phase 7.5, then updating the fields: `resume_text`, `skills`, `experience_years`, `education`, `preferred_roles`.
  - Returns the updated `user_profiles` document.

- **New Service Module**: `backend/services/resume_service.py`
  - `extract_text_from_pdf(file_bytes: bytes) -> str`: Uses pdfplumber to extract raw text.
  - `parse_resume_with_llm(resume_text: str) -> dict`: Uses `get_llm()` + PydanticOutputParser to extract structured fields. Follows the project's established retry-once-then-fallback pattern.
  - `validate_pdf(file_bytes: bytes) -> None`: Checks magic bytes and file size.

- **New Prompt Template**: `backend/prompts/resume_prompt.py`
  - System prompt for the LLM, instructing it to extract skills, experience_years, education, and preferred_roles from resume text, outputting structured JSON per the PydanticOutputParser format instructions.

- **New Pydantic Models**: Added to `backend/schemas/profile.py`
  - `ResumeExtractedData`: Pydantic model for the LLM output parser (skills, experience_years, education, preferred_roles).
  - `ResumeUploadResponse`: Response model for the upload endpoint (mirrors `UserProfileResponse`).

- **New Database Helper**: Added to `backend/database/user_profiles.py`
  - `update_profile_by_user_id(user_id, update_fields)`: Updates specific fields on an existing profile document matched by `user_id`.

- **New Dependency**: `pdfplumber` added to `backend/requirements.txt`.

## Design Decision: pdfplumber over PyPDF2

**Choice: pdfplumber**

| Factor | pdfplumber | PyPDF2 |
|---|---|---|
| Text extraction quality | Superior — maintains layout, handles tables, multi-column text | Basic — often merges lines, loses whitespace structure |
| Handling edge cases | Robust with scanned-text PDFs, complex layouts | Frequently produces garbled output on non-trivial layouts |
| API simplicity | `page.extract_text()` — one call per page | `page.extract_text()` — similar API but worse results |
| Maintenance | Actively maintained, well-documented | History of abandonment/forks; `pypdf` is the successor |
| Resume-specific fitness | Resumes have columns, tables, headers — pdfplumber handles these well | Struggles with the multi-column layouts common in resumes |

For a resume parsing use case where text quality directly impacts LLM extraction accuracy, pdfplumber's superior layout handling is the correct choice.

## Capabilities

### New Capabilities
- `resume-upload`: Ability for authenticated users to upload a PDF resume and have it automatically parsed into structured profile fields.
- `pdf-text-extraction`: Extract raw text from PDF documents using pdfplumber.
- `resume-llm-parsing`: Use the LLM to convert unstructured resume text into structured skills, experience, education, and role preferences.

## Impact

- `backend/requirements.txt`: Add `pdfplumber`.
- `backend/services/resume_service.py`: **[NEW]** PDF validation, text extraction, and LLM-based resume parsing logic.
- `backend/prompts/resume_prompt.py`: **[NEW]** System prompt template for resume extraction.
- `backend/schemas/profile.py`: Add `ResumeExtractedData` and `ResumeUploadResponse` models.
- `backend/database/user_profiles.py`: Add `update_profile_by_user_id()` helper.
- `backend/api/v1/profiles.py`: Add the `POST /profile/upload-resume` route handler.
- `backend/api/v1/router.py`: Add a new `profile` router (singular, for `/profile/upload-resume`) alongside the existing `profiles` router.
- `backend/tests/test_resume_upload.py`: **[NEW]** Test suite covering upload validation, text extraction, LLM parsing, and end-to-end endpoint behavior.
- Does **NOT** touch: `backend/tools/`, `frontend/`, `backend/agents/` (the resume parsing logic lives in `services/` as it's a service, not a reusable agent in the LangGraph pipeline).
