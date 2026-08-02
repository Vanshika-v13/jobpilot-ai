## 1. Dependency & Configuration

- [x] 1.0 Add `pdfplumber` to `backend/requirements.txt`.
- [x] 1.1 Install the dependency (`pip install pdfplumber`).

## 2. Pydantic Schemas

- [x] 2.0 Add `ResumeExtractedData` model to `backend/schemas/profile.py`:
  - `skills: List[str]` (default: empty list)
  - `experience_years: float` (default: 0.0)
  - `education: str` (default: "")
  - `preferred_roles: List[str]` (default: empty list)
  - This model is used as the `PydanticOutputParser` target for LLM extraction.
- [x] 2.1 Add `ResumeUploadResponse` model to `backend/schemas/profile.py`:
  - Same shape as `UserProfileResponse` (can alias or inherit).
  - Used as the response model for the upload endpoint.

## 3. Database Helper

- [x] 3.0 Add `update_profile_by_user_id(user_id: str, update_fields: dict)` to `backend/database/user_profiles.py`:
  - Finds the profile by `user_id` and applies `$set` with the given fields + `updated_at`.
  - Returns the updated document (using `find_one_and_update` with `return_document=ReturnDocument.AFTER`).

## 4. Prompt Template

- [x] 4.0 Create `backend/prompts/resume_prompt.py` with `RESUME_EXTRACTION_PROMPT`:
  - Instructs the LLM to extract `skills`, `experience_years`, `education`, and `preferred_roles` from raw resume text.
  - Includes `{resume_text}` and `{format_instructions}` placeholders.
  - Explicitly instructs the LLM to only extract what is stated in the text — no fabrication.
  - Provides guidance on how to determine `experience_years` (sum of individual job durations, or stated total).
  - Provides guidance on `preferred_roles` (infer from recent job titles, stated objectives, or career summary if present — otherwise return empty list).

## 5. Resume Service

- [x] 5.0 Create `backend/services/resume_service.py` with:

  **`validate_pdf(file_bytes: bytes) -> None`**:
  - Check `len(file_bytes) > 5 * 1024 * 1024` → raise `ValueError("File too large. Maximum size is 5 MB.")`.
  - Check `file_bytes[:5] != b"%PDF-"` → raise `ValueError("Invalid file type. Only PDF files are accepted.")`.

  **`extract_text_from_pdf(file_bytes: bytes) -> str`**:
  - Open the PDF from bytes using `pdfplumber.open(io.BytesIO(file_bytes))`.
  - Iterate over all pages, call `page.extract_text()`, concatenate with newlines.
  - If total extracted text is fewer than 50 characters, raise `ValueError("No readable text found in PDF.")`.
  - Truncate to 8,000 characters max before returning (to prevent LLM context overflow).
  - Wrap pdfplumber errors in a clear `ValueError("Could not extract text from PDF. The file may be corrupt or image-based.")`.

  **`parse_resume_with_llm(resume_text: str) -> dict`**:
  - Import and use `get_llm()` from `agents.llm_provider`.
  - Create `PydanticOutputParser(pydantic_object=ResumeExtractedData)`.
  - Format the prompt with `RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text, format_instructions=parser.get_format_instructions())`.
  - `await llm.ainvoke(prompt)` → `parser.invoke(response)`.
  - Validate that at least `skills` or `education` is non-empty. If both are empty, raise `ValueError`.
  - **On failure**: Retry once with the stricter "CRITICAL: Respond with valid JSON ONLY" suffix (matching existing agent pattern).
  - **On retry failure**: Raise `RuntimeError("Failed to extract profile data from resume.")`.
  - Return the parsed data as a dict via `model_dump()`.

## 6. API Endpoint

- [x] 6.0 Create the upload route in `backend/api/v1/profiles.py` (add to existing router):
  - `@router.post("/upload-resume", response_model=ResumeUploadResponse)`
  - Parameters: `file: UploadFile`, `user_id: str = Depends(get_current_user)`.
  - Read file bytes: `file_bytes = await file.read()`.
  - Call `validate_pdf(file_bytes)` — catch `ValueError`, return appropriate HTTP 400/413.
  - Call `extract_text_from_pdf(file_bytes)` — catch `ValueError`, return HTTP 400.
  - Call `await parse_resume_with_llm(resume_text)` — catch `RuntimeError`, return HTTP 502.
  - Call `get_or_create_profile(user_id)` to ensure profile exists.
  - Call `update_profile_by_user_id(user_id, {resume_text, skills, experience_years, education, preferred_roles})`.
  - Return the updated profile document.

- [x] 6.1 Create `backend/api/v1/profile.py` as a separate router file for the singular `/profile` prefix:
  - Contains only the `POST /upload-resume` route (which mounts at `/api/v1/profile/upload-resume`).
  - Update `backend/api/v1/router.py` to import and include this new `profile.router` under the `/profile` prefix alongside the existing `/profiles` router.

## 7. Testing

- [x] 7.0 Create `backend/tests/test_resume_upload.py` with the following test cases:

  **Validation tests:**
  - Test rejection of files exceeding 5 MB.
  - Test rejection of non-PDF files (e.g., a PNG renamed to `.pdf`) by magic-byte check.
  - Test acceptance of a valid small PDF.

  **Text extraction tests:**
  - Test that `extract_text_from_pdf` returns expected text from a known test PDF.
  - Test that an image-only or empty PDF raises a clear error.
  - Test that text is truncated to 8,000 characters for very long PDFs.

  **LLM parsing tests (mocked):**
  - Mock `get_llm()` to return a controlled response.
  - Test that `parse_resume_with_llm` correctly parses the mocked LLM output into `ResumeExtractedData`.
  - Test the retry path: first call fails, retry succeeds.
  - Test the full-failure path: both calls fail, `RuntimeError` is raised.

  **Endpoint integration tests (mocked LLM + DB):**
  - Test the full `POST /profile/upload-resume` flow with a valid PDF, mocked LLM, and mocked DB.
  - Test that unauthenticated requests return 401.
  - Test that the profile is updated with extracted data.
  - Test error responses for corrupt PDF, empty PDF, LLM failure.

- [x] 7.1 Create a small test PDF fixture in `backend/tests/fixtures/` for use in tests.

- [x] 7.2 Run the full pytest suite to verify no regressions: `pytest backend/tests/ -v`.

