## ADDED Requirements

### Requirement: Wellfound Search Navigation and Raw Extraction
The system SHALL provide an async browser automation tool (`backend/tools/wellfound.py`) using Playwright to search for startup jobs on Wellfound by role and location, returning a list of raw listing objects.

#### Scenario: Successful search query execution
- **WHEN** `scrape_wellfound(role="software engineer", location="remote")` is called
- **THEN** the Playwright browser navigates to Wellfound search results, waits for job listing components to render dynamically, and returns a list of dictionaries with `raw_html`, `url`, `source` set to "wellfound", and `scraped_at` timestamp.

#### Scenario: Dynamic DOM rendering wait and failure handling
- **WHEN** `scrape_wellfound` encounters loading delays, popups, or cloudflare anti-bot checks
- **THEN** the scraper waits up to the designated timeout before returning whatever partial raw listings were retrieved or an empty list `[]` without raising unhandled errors.

#### Scenario: Maximum results pagination limit
- **WHEN** `scrape_wellfound` is invoked with `max_results=10`
- **THEN** the returned raw listing list contains at most 10 item payloads.
