## ADDED Requirements

### Requirement: Generate Interview Questions
The system SHALL generate a configurable number of role-specific interview questions (default 10) for a given job.

#### Scenario: Generate questions successfully
- **WHEN** a valid job ID and optional `question_count` (default 10) are provided to the interview questions endpoint
- **THEN** the system generates exactly `question_count` questions, split `round(question_count * 0.7)` technical and the remainder HR/behavioral
- **AND** the prompt template dynamically inserts the total, technical, and HR counts (no hardcoded numbers)
- **AND** each question includes a specific topic string and a difficulty level (easy, medium, or hard)

### Requirement: Cache Interview Questions
The system SHALL cache generated interview questions on the job record to prevent redundant processing.

#### Scenario: Retrieve cached questions
- **WHEN** the interview questions endpoint is called for a job that already has cached questions
- **THEN** the system returns the cached questions immediately without invoking the LLM

### Requirement: Robust LLM Parsing
The system SHALL handle LLM generation and parsing failures robustly without silent truncation.

#### Scenario: Retry on invalid format
- **WHEN** the LLM returns an improperly formatted response or empty fields
- **THEN** the agent automatically retries the generation before failing gracefully

### Requirement: Safety and Sanitization
The system SHALL sanitize job descriptions before sending them to the LLM.

#### Scenario: Sanitize raw description
- **WHEN** preparing the prompt for the Interview Agent
- **THEN** the `raw_description` is processed through the `sanitize_description()` utility
