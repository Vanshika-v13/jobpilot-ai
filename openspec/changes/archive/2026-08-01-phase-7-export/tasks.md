## 1. Setup and Server Configuration

- [x] 1.0 Create `backend/static/exports` directory and update the root `/backend/.gitignore` to ignore `static/exports/*.xlsx` and `static/exports/*.pdf`.
- [x] 1.1 Update `backend/main.py` to import `StaticFiles` from `fastapi.staticfiles` and mount it at `/static` pointing to `backend/static`.

## 2. API Contract and Routing

- [x] 2.0 Create `backend/schemas/export.py` defining `ExportRequest` (accepts `job_ids: List[str]`, `format: str`) and `ExportResponse` (returns `file_url: str`, `format: str`, `job_count: int`).
- [x] 2.1 Create router file `backend/api/v1/export.py` defining the `POST /` route.
- [x] 2.2 Include the export router under `/export` prefix in `backend/api/v1/router.py`.

## 3. Export Logic Implementation

- [x] 3.0 Create `backend/agents/export_agent.py`.
- [x] 3.1 Implement async job collection fetching from MongoDB, supporting query by `job_ids` list and graceful default fallback values for missing fields.
- [x] 3.2 Implement `generate_excel_report(jobs: List[dict], filepath: str)` using `openpyxl`, with customized table formatting and dynamic column widths.
- [x] 3.3 Implement `generate_pdf_report(jobs: List[dict], filepath: str)` using `reportlab.platypus` classes, styling individual job sections professionally.
- [x] 3.4 Implement deterministic file hashing logic (using md5/sha256 on sorted job_ids + format) to determine filenames and avoid duplicate exports.

## 4. Verification and Testing

- [x] 4.0 Create `backend/tests/test_export_agent.py` to test file generation formats, handling of missing fields, and file contents.
- [x] 4.1 Create `backend/tests/test_export_endpoint.py` to test `POST /api/v1/export` responses, payload validation, and static file download verification.
- [x] 4.2 Run the full pytest suite using the project's virtual environment.
