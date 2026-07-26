## 1. Setup & Environment

- [x] 1.1 Ensure `playwright` is present in `backend/requirements.txt` and install Chromium browser binaries if needed.
- [x] 1.2 Update `backend/tools/__init__.py` to expose `scrape_internshala`, `scrape_wellfound`, and `scrape_unstop`.
- [x] 1.3 Implement a shared rate-limiting/delay utility in `backend/tools/utils.py` that adds a random delay (e.g. 2-5 seconds) between page navigations and actions. All three scrapers must use this utility between requests.

## 2. Internshala Scraper Module

- [x] 2.1 Create `backend/tools/internshala.py` with `async def scrape_internshala(role: str, location: str, max_results: int = 20) -> list[dict]`.
- [x] 2.2 Construct query URL for Internshala internship/job search based on role and location input.
- [x] 2.3 Launch async Playwright Chromium browser, navigate to search results using `backend/tools/utils.py` rate-limiting delay between page actions, and locate job listing card elements.
- [x] 2.4 Capture raw HTML snippets (`raw_html`), listing URLs (`url`), and source tag (`"internshala"`) for up to `max_results` listings.
- [x] 2.5 Add try/except exception handling to return an empty list `[]` on navigation timeout or page structure errors.

## 3. Wellfound Scraper Module

- [x] 3.1 Create `backend/tools/wellfound.py` with `async def scrape_wellfound(role: str, location: str, max_results: int = 20) -> list[dict]`.
- [x] 3.2 Construct search URL and configure browser context (User-Agent, viewport) for SPA dynamic rendering.
- [x] 3.3 Launch async Playwright browser, navigate to Wellfound search page using `backend/tools/utils.py` rate-limiting delay between page actions, and wait for job component selectors.
- [x] 3.4 Capture raw HTML/JSON listing payloads (`raw_html`), listing URLs (`url`), and source tag (`"wellfound"`) for up to `max_results` listings.
- [x] 3.5 Add try/except exception handling to return an empty list `[]` on navigation timeout or anti-bot/selector errors.

## 4. Unstop Scraper Module

- [x] 4.1 Create `backend/tools/unstop.py` with `async def scrape_unstop(role: str, location: str, max_results: int = 20) -> list[dict]`.
- [x] 4.2 Construct search URL for Unstop opportunities based on role and location input.
- [x] 4.3 Launch async Playwright browser, navigate to Unstop search page using `backend/tools/utils.py` rate-limiting delay between page actions, and wait for opportunity card selectors.
- [x] 4.4 Capture raw HTML/JSON listing payloads (`raw_html`), listing URLs (`url`), and source tag (`"unstop"`) for up to `max_results` listings.
- [x] 4.5 Add try/except exception handling to return an empty list `[]` on navigation timeout or selector errors.

## 5. Verification & Testing

- [x] 5.1 Create `backend/tests/test_internshala.py` to test `scrape_internshala` (marking live network scraper calls with `@pytest.mark.integration` or `@pytest.mark.live` for manual execution only).
- [x] 5.2 Create `backend/tests/test_wellfound.py` to test `scrape_wellfound` (marking live network scraper calls with `@pytest.mark.integration` or `@pytest.mark.live` for manual execution only).
- [x] 5.3 Create `backend/tests/test_unstop.py` to test `scrape_unstop` (marking live network scraper calls with `@pytest.mark.integration` or `@pytest.mark.live` for manual execution only).
- [x] 5.4 Save sample raw HTML/JSON responses from the initial successful live run as fixture files in `backend/tests/fixtures/` (`internshala_sample.html`, `wellfound_sample.html`, `unstop_sample.html`).
- [x] 5.5 Implement unit test cases that load saved HTML/JSON fixture files from `backend/tests/fixtures/` so routine test runs validate output structures fast and deterministically without re-scraping live portals every time.
- [x] 5.6 Run pytest suite on `backend/tests/` to verify routine unit tests pass using fixtures and live integration tests run cleanly when explicitly invoked.


