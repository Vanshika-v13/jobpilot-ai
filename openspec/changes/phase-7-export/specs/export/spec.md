## ADDED Requirements

### Requirement: Excel Job Export
The system SHALL export selected job listings to an Excel spreadsheet using `openpyxl`.

#### Scenario: Export to Excel successfully
- **WHEN** the export endpoint is requested with format "excel"
- **THEN** the system generates an Excel sheet where each row is a job listing
- **AND** the columns include: Company, Role, Location, Salary, Relevance Score, Skill Match Score, Matched Skills, Missing Skills, Apply Link
- **AND** the header row is formatted with a distinct background fill and bold font

### Requirement: PDF Job Export
The system SHALL export selected job listings to a formatted PDF report using `reportlab`.

#### Scenario: Export to PDF successfully
- **WHEN** the export endpoint is requested with format "pdf"
- **THEN** the system generates a PDF document structured with one distinct section per job
- **AND** each section presents the job title, company, salary, and structured tables or lists of matched/missing skills for readability

### Requirement: API Contract and Caching
The system SHALL serve exported files statically and return the URL to the client.

#### Scenario: Request export file URL
- **WHEN** a valid list of job IDs is sent via POST request to `/api/v1/export`
- **THEN** the system generates the corresponding file locally
- **AND** returns a JSON response containing `file_url`, `format`, and `job_count`
- **AND** the file is downloadable via the returned static `file_url`
- **AND** identical lists of job IDs and formats result in the same deterministic file path, preventing duplicate file generation on disk

### Requirement: Graceful Fallbacks
The system SHALL handle missing jobs or missing optional analysis fields gracefully.

#### Scenario: Export with incomplete job data
- **WHEN** a job is missing optional analytical fields (e.g. `skill_match_score`, `matched_skills`)
- **THEN** the export compilation defaults those fields to "N/A" or empty lists rather than raising an error
- **AND** successfully compiles the rest of the job details into the output file
