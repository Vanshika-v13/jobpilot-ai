## ADDED Requirements

### Requirement: Internshala Search Navigation and Raw Extraction
The system SHALL provide an async browser automation tool (`backend/tools/internshala.py`) using Playwright to search for internships and jobs on Internshala by role and location, returning a list of raw listing objects.

#### Scenario: Successful search query execution
- **WHEN** `scrape_internshala(role="backend developer", location="bangalore")` is called
- **THEN** the Playwright browser navigates to the Internshala search results page for the specified query, locates listing container elements, and returns a list of dictionaries with `raw_html`, `url`, `source` set to "internshala", and `scraped_at` timestamp.

#### Scenario: No results or invalid location handling
- **WHEN** `scrape_internshala` encounters no search results or page navigation timeouts
- **THEN** the function handles the exception gracefully and returns an empty list `[]` without throwing an unhandled exception.

#### Scenario: Maximum results pagination limit
- **WHEN** `scrape_internshala` is invoked with `max_results=5`
- **THEN** the returned raw listing list contains at most 5 item payloads.
