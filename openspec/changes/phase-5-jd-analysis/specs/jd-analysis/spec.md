## ADDED Requirements

### Requirement: JD Analysis and Skill Gap Extraction
The system SHALL accept a job ID and a profile ID, retrieve the job description, sanitize the description text, use the configured LLM to extract structured details (required skills, preferred_skills, experience required, responsibilities, important keywords), compare those skills to the user's profile skills, and produce a match score, list of matched and missing skills, and learning priorities.

#### Scenario: Successful analysis of a job description
- **WHEN** a job is analyzed against a profile containing matching and missing skills
- **THEN** the system SHALL return the skill match score, list of matched skills, missing skills, and learning priorities.

### Requirement: Database Caching of Analysis Results
The system SHALL cache the analysis results (skill_match_score, matched_skills, missing_skills, learning_priority, and jd_summary) to the job's document in the MongoDB jobs collection. Subsequent requests SHALL return the cached results directly without invoking the LLM.

#### Scenario: Return cached results on duplicate request
- **WHEN** a job analysis request is received for a job that has already been analyzed
- **THEN** the system SHALL return the cached analysis results from MongoDB instead of calling the LLM.

### Requirement: Sanitize Description Content
The system SHALL sanitize the job's `raw_description` to remove potentially hazardous HTML tags or script injection vectors prior to LLM processing.

#### Scenario: Safety check on contaminated description
- **WHEN** a job description containing scripts or unsafe HTML is analyzed
- **THEN** the system SHALL strip the unsafe markup before sending it to the LLM.
