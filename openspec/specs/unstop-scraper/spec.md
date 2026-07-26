## ADDED Requirements

### Requirement: Unstop Search Navigation and Raw Extraction
The system SHALL provide an async browser automation tool (`backend/tools/unstop.py`) using Playwright to search for jobs and internships on Unstop by role and location, returning a list of raw listing objects.

#### Scenario: Successful search query execution
- **WHEN** `scrape_unstop(role="data scientist", location="delhi")` is called
- **THEN** the Playwright browser navigates to Unstop job listings, handles dynamic content rehydration, and returns a list of dictionaries with `raw_html`, `url`, `source` set to "unstop", and `scraped_at` timestamp.

#### Scenario: Timeout and element missing resilience
- **WHEN** `scrape_unstop` fails to find listing elements or encounters network connection failures
- **THEN** the tool logs the warning and returns an empty list `[]` without crashing the application.

#### Scenario: Maximum results limit
- **WHEN** `scrape_unstop` is called with `max_results=5`
- **THEN** the returned raw listing list contains at most 5 item payloads.
