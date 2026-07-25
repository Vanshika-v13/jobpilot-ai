## Context

In Phase 1, the FastAPI backend core was initialized and verified with health endpoints and DB connection setup. Phase 2 focuses on creating the browser automation scraping layer using Playwright (`async_playwright`). 

Each portal (Internshala, Wellfound, Unstop) renders job and internship listings differently—some via server-rendered HTML cards and others via client-side SPA rehydration or background API requests. The scrapers built in this phase serve as raw data collectors for downstream consumption.

## Goals / Non-Goals

**Goals:**
- Implement three independent Playwright scraper modules under `backend/tools/`:
  - `internshala.py` -> `scrape_internshala(role: str, location: str, max_results: int = 20) -> list[dict]`
  - `wellfound.py` -> `scrape_wellfound(role: str, location: str, max_results: int = 20) -> list[dict]`
  - `unstop.py` -> `scrape_unstop(role: str, location: str, max_results: int = 20) -> list[dict]`
- Standardize the scraper output contract: returns a list of dictionaries containing raw HTML string snippets (`raw_html`), listing page URL (`url`), portal source (`source`), and scrape metadata (`scraped_at`).
- Ensure robust async browser context management (auto-closing browser/pages, handling navigation timeouts gracefully).
- Provide unit and integration test coverage in `backend/tests/` for each scraper module.

**Non-Goals:**
- Extract structured schema fields (company, role, skills, salary, experience) — schema normalization belongs to Phase 3 (Extraction Agent).
- Implement any LLM, LangChain, or agent logic.
- Store results in MongoDB or update `job_searches`/`jobs` collections.
- Create FastAPI REST routes for search execution (Phase 4).
- Touch `frontend/`, `backend/agents/`, or `backend/database/`.

## Decisions

### 1. Library Choice: Async Playwright (`playwright.async_api`)
- **Choice**: `playwright.async_api` (`async_playwright`)
- **Rationale**: FastAPI runs an asynchronous event loop. Using async Playwright avoids blocking worker threads and seamlessly integrates with FastAPI's async execution paradigm. Playwright offers native handling for modern JS heavy applications (Wellfound/Unstop), wait-for-selector capabilities, and web request interception if needed.
- **Alternatives**: BeautifulSoup / requests (fails on JS-rendered SPAs like Wellfound/Unstop), Selenium (heavier footprint, slower than Playwright).

### 2. Output Payload Design (Unnormalized Raw Content)
- **Choice**: Raw dictionary list per scraper call containing:
  ```json
  {
    "source": "internshala | wellfound | unstop",
    "raw_html": "<div class=\"individual_internship\">...</div>",
    "url": "https://...",
    "scraped_at": "2026-07-25T17:10:00Z"
  }
  ```
- **Rationale**: Keeps scraping decoupled from AI parsing logic. The Playwright scraper is purely responsible for page navigation, element selection, and raw DOM capture. Extraction Agent (Phase 3) will handle converting this raw payload into structured `jobs` documents.
- **Alternatives**: Normalizing fields inside Playwright tools (violates single responsibility, hardcodes regex/selectors for complex fields like skills).

### 3. Navigation Strategy and Resilience
- **Choice**: Configurable timeout (default 30 seconds), headless browser mode by default, standard desktop User-Agent headers, and selector fallback handling.
- **Rationale**: Portals frequently update minor class names or introduce popups. If search results yield 0 elements or time out, scrapers must return an empty list or captured partial listings without crashing the server process.

### 4. Code Organization
- **Choice**:
  - `backend/tools/utils.py` (shared rate-limiting and helper utilities)
  - `backend/tools/internshala.py`
  - `backend/tools/wellfound.py`
  - `backend/tools/unstop.py`
  - `backend/tools/__init__.py`
  - `backend/tests/test_scrapers.py`
- **Rationale**: Matches the architecture specified in `docs/architecture.md` and phase instructions in `docs/phases.md`.

### 5. Shared Rate-Limiting & Delay Utility (`backend/tools/utils.py`)
- **Choice**: Shared helper function `random_delay(min_seconds: float = 2.0, max_seconds: float = 5.0)` called before/between Playwright navigations and element interactions across all scrapers.
- **Rationale**: Prevents IP rate-limiting and anti-bot triggers on target portals by humanizing request timing.

### 6. Live DOM Selector Verification
- **Note**: All target CSS/XPath selectors and DOM container structures used in `internshala.py`, `wellfound.py`, and `unstop.py` were verified against live target sites on **2026-07-25**. Exact selectors are documented as inline top-level comments within each scraper module for maintainability when target portals update their markup.

### 8. Unstop: Public API Instead of DOM Scraping
- **Choice**: Use Unstop's public search API (`https://unstop.com/api/public/opportunity/search-new`) via `httpx` instead of Playwright-based DOM scraping.
- **Rationale**: Unstop is an Angular SPA that renders job listings with dynamically-generated CSS class names and heavy client-side hydration. DOM selectors broke across page loads (class names like `.cdk-overlay-*`, `.ng-tns-c*`) making Playwright scraping unreliable. Inspection of network traffic revealed the same structured JSON endpoint the Angular frontend consumes, which returns stable, pre-structured fields (title, company, locations, salary, skills, description) directly.
- **Output contract fork**: Because the API returns structured JSON, `unstop.py` produces a different payload shape than the other two scrapers:
  - **Unstop** returns: `source`, `structured: true`, `title`, `company`, `location`, `salary`, `skills`, `description`, `raw_html` (serialised API JSON for reference), `url`, `scraped_at`.
  - **Internshala / Wellfound** return: `source`, `raw_html` (actual HTML snippet), `url`, `scraped_at`.
  The Extraction Agent (Phase 3) should detect the `"structured": true` flag (or absence of raw HTML content) and apply direct field mapping for Unstop listings — no LLM parsing call required, saving one LLM invocation per Unstop result.
- **Alternatives**: Continued DOM scraping with broader selectors (fragile, breaks on Angular rebuilds), server-side rendering via Playwright `page.content()` after full hydration (slow, 8–12s per page, still requires complex selectors).

### 7. Dual-Mode Testing Strategy (Live Integration vs Saved HTML Fixtures)
- **Choice**:
  - Live network scraper tests are explicitly decorated with `@pytest.mark.integration` / `@pytest.mark.live` and excluded from routine CI/dev pytest runs.
  - Raw HTML/JSON payloads captured during initial live execution are saved to `backend/tests/fixtures/` (`internshala_sample.html`, `wellfound_sample.html`, `unstop_sample.html`).
  - Routine unit tests execute deterministically against `backend/tests/fixtures/` without invoking real network requests or live Playwright navigations.
- **Rationale**: Prevents flaky routine test runs, avoids unnecessary portal rate-limiting during local development, and ensures parsing logic can be verified fast offline.

## Risks / Trade-offs


- **[Risk] Anti-bot detection / Rate limiting on portals (especially Wellfound / Internshala)**
  - *Mitigation*: Use standard browser headers (User-Agent, Accept-Language), random delays via `backend/tools/utils.py` (2-5s) between page actions, and graceful fallback return (empty list on anti-bot captcha/challenge pages).
- **[Risk] Portal DOM Structure Changes**
  - *Mitigation*: Keep selectors broad and fall back to container elements to capture full card HTML snippets. Selectors verified live on 2026-07-25.
- **[Risk] Playwright Browser Executable Dependencies**
  - *Mitigation*: Ensure `playwright install chromium` command is documented and executable in the environment.

## Open Questions

- None. Scope is clear and strictly restricted to pure Playwright navigation for the three portals.

