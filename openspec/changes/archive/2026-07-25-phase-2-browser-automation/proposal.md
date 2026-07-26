## Why

To enable automated multi-portal job discovery, the system requires resilient browser automation modules capable of navigating search pages, handling dynamic JS rendering, applying filters, and extracting raw job listings. Phase 2 introduces standalone Playwright scraper modules for Internshala, Wellfound, and Unstop.

## What Changes

- Implement async Playwright scraper module for Internshala in `backend/tools/internshala.py`.
- Implement async Playwright scraper module for Wellfound in `backend/tools/wellfound.py`.
- Implement async Playwright scraper module for Unstop in `backend/tools/unstop.py`.
- Add test suite in `backend/tests/` to verify scraper navigation, query parameter handling, raw data extraction, and graceful failure handling.
- Update `backend/requirements.txt` with `playwright` dependency if required.
- Standardize the scraper call interface: each module accepts search parameters (`role`, `location`) and returns raw HTML snippets or JSON payloads per listing without schema normalization or LLM involvement.

## Capabilities

### New Capabilities

- `internshala-scraper`: Async Playwright browser automation module targeting Internshala search results to retrieve raw listing payloads.
- `wellfound-scraper`: Async Playwright browser automation module targeting Wellfound search results to retrieve raw listing payloads.
- `unstop-scraper`: Async Playwright browser automation module targeting Unstop search results to retrieve raw listing payloads.

### Modified Capabilities

_(none — no existing scraper capabilities in specs)_

## Impact

- **Affected Files:** `backend/tools/internshala.py`, `backend/tools/wellfound.py`, `backend/tools/unstop.py`, `backend/tools/__init__.py`, `backend/tests/test_scrapers.py` (or individual test files), `backend/requirements.txt`.
- **Dependencies:** `playwright` Python library and Playwright browser binaries (chromium/firefox/webkit).
- **Scope Isolation:** Strictly limited to `backend/tools/` and `backend/tests/`. No database persistence, no LLM/agent logic, no API endpoints, and zero interaction with `frontend/`.
