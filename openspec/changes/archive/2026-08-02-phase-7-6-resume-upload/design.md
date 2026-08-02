## Context

Phase 7.6 adds resume upload functionality to JobPilot AI. An authenticated user can upload a PDF resume, which the system extracts text from, parses into structured profile data using the LLM, and saves to the user's profile. This complements (but does not replace) the manual profile entry via `POST /api/v1/profiles`.

The endpoint follows the existing security model from Phase 7.5 (JWT auth via `get_current_user`), the established LLM invocation pattern from the agents layer (PydanticOutputParser + format_instructions + retry-once + graceful-fallback), and the database access patterns from `user_profiles.py`.

## Goals / Non-Goals

**Goals:**
- Implement `POST /api/v1/profile/upload-resume` as specified in `api.md`.
- Accept PDF uploads via multipart/form-data with a 5 MB file size limit.
- Validate that uploads are actual PDFs using magic-byte verification (not filename-based).
- Extract raw text from the PDF using pdfplumber.
- Use `get_llm()` + PydanticOutputParser to extract structured fields: `skills`, `experience_years`, `education`, `preferred_roles`.
- Save extracted data into the user's `user_profiles` document via `get_or_create_profile()` + `update_profile_by_user_id()`.
- Handle all failure modes gracefully: corrupt PDFs, empty text, LLM failures, malformed LLM output.
- Keep resume upload fully optional — manual profile creation remains the primary path.

**Non-Goals:**
- Supporting non-PDF formats (DOCX, images, etc.) — PDF only for V1.
- OCR for scanned/image-based PDFs — pdfplumber extracts text-layer content only.
- Storing the original PDF file (we store only the extracted `resume_text`).
- Replacing or deprecating the manual `POST /api/v1/profiles` endpoint.
- Touching `backend/tools/` or `frontend/`.

## Decisions

### PDF Library: pdfplumber

pdfplumber is chosen over PyPDF2 for the following reasons:
1. **Text quality**: pdfplumber preserves layout structure, handles multi-column resumes, and produces cleaner text that the LLM can parse more accurately.
2. **Resume fitness**: Resumes commonly use tables, columns, and complex formatting. pdfplumber handles these layouts; PyPDF2 frequently produces garbled or merged text.
3. **Maintenance**: pdfplumber is actively maintained. PyPDF2 has a history of abandonment (its successor is `pypdf`).
4. **API**: Both have similar APIs (`page.extract_text()`), but pdfplumber's output is consistently better for our use case.

### Service Layer Placement (not Agents)

The resume parsing logic goes in `backend/services/resume_service.py`, not `backend/agents/`. Rationale:
- The agents layer (`backend/agents/`) contains LangChain/LangGraph agent definitions that participate in the multi-step search/analysis pipeline (Planner → Scrape → Extract → Rank → Analyze).
- Resume parsing is a standalone utility invoked by a single endpoint. It does not participate in the agent graph. Placing it in `services/` follows the architecture's separation: "services/ — Business logic. Orchestrates agent calls, manages search lifecycle."
- The service still uses `get_llm()` from `agents/llm_provider.py` — this is the shared LLM factory, not an agent-specific dependency.

### File Validation Strategy

1. **Size check**: Reject files > 5 MB immediately (before reading the full content into memory). FastAPI's `UploadFile` provides the content-type and filename, but we read and check actual byte size.
2. **Magic bytes**: Read the first 5 bytes and verify they match `%PDF-` (the PDF magic signature). This catches renamed non-PDF files that might have a `.pdf` extension or `application/pdf` content-type.
3. **Content-type header**: Also checked as a secondary signal, but not relied upon exclusively (it can be spoofed by clients).

### LLM Extraction Pattern

Follow the exact same pattern used by `extraction_agent.py`, `jd_analysis_agent.py`, and `interview_agent.py`:

```python
# 1. Define Pydantic model for expected output
class ResumeExtractedData(BaseModel):
    skills: List[str] = Field(default_factory=list)
    experience_years: float = Field(default=0.0)
    education: str = Field(default="")
    preferred_roles: List[str] = Field(default_factory=list)

# 2. Create parser with format_instructions
parser = PydanticOutputParser(pydantic_object=ResumeExtractedData)

# 3. Build prompt with {format_instructions} placeholder
prompt = RESUME_EXTRACTION_PROMPT.format(
    resume_text=resume_text,
    format_instructions=parser.get_format_instructions()
)

# 4. Invoke LLM
response = await llm.ainvoke(prompt)
extracted = parser.invoke(response)

# 5. Validate core fields are not all empty
if not extracted.skills and not extracted.education:
    raise ValueError("All core fields empty. Likely a parsing failure.")

# 6. On failure: retry once with stricter prompt
# 7. On retry failure: return clear error, do NOT save garbage
```

### Profile Update Semantics

- Use `get_or_create_profile(user_id)` to find or create the profile (reusing Phase 7.5 helper).
- Update only the resume-relevant fields: `resume_text`, `skills`, `experience_years`, `education`, `preferred_roles`, `updated_at`.
- **Overwrite strategy**: The resume upload overwrites these specific fields entirely. If a user had manually entered skills and then uploads a resume, the resume-extracted skills replace the manual ones. This is the expected behavior — the resume is the authoritative source when used.
- Fields not extracted from the resume (`preferred_locations`, `preferred_location`) are left untouched.

### Error Response Design

| Scenario | HTTP Status | Response |
|---|---|---|
| No file uploaded | 422 | FastAPI's default validation error |
| File exceeds 5 MB | 413 | `{"detail": "File too large. Maximum size is 5 MB."}` |
| File is not a PDF (magic bytes) | 400 | `{"detail": "Invalid file type. Only PDF files are accepted."}` |
| pdfplumber fails (corrupt PDF) | 400 | `{"detail": "Could not extract text from PDF. The file may be corrupt or image-based."}` |
| Extracted text is empty/too short | 400 | `{"detail": "No readable text found in PDF. The file may be image-based or empty."}` |
| LLM extraction fails (both attempts) | 502 | `{"detail": "Failed to extract profile data from resume. Please try again or update your profile manually."}` |
| Unauthenticated | 401 | Standard JWT 401 from `get_current_user` |

### Minimum Text Threshold

After text extraction, reject PDFs that produce fewer than 50 characters of text. This catches image-only PDFs, blank pages, or corrupt files that pdfplumber opens but extracts nothing useful from.

## Risks / Trade-offs

- **Risk**: pdfplumber cannot extract text from image-based (scanned) PDFs.
  - *Mitigation*: Return a clear error message suggesting the user has an image-based PDF. OCR support is out of scope for V1.
- **Risk**: LLM may hallucinate skills or experience not present in the resume.
  - *Mitigation*: The prompt will explicitly instruct the LLM to extract only what is stated in the resume text, not to infer or fabricate. Users can review and manually edit their profile after upload.
- **Risk**: Large PDFs (close to 5 MB) may produce very long text that causes LLM context overflow.
  - *Mitigation*: Truncate extracted text to 8,000 characters before sending to the LLM (similar to `TRUNCATION_THRESHOLD` pattern used in `jd_analysis_agent.py` and `interview_agent.py`).
- **Risk**: Resume upload overwrites manually-entered profile fields.
  - *Mitigation*: This is documented and intentional behavior. The resume is treated as the authoritative source when used. Users who want fine-grained control should use the manual endpoint.
