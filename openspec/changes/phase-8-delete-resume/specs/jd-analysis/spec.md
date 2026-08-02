## ADDED Requirements

### Requirement: Analysis response indicates whether the user profile has skills
The system SHALL include a `profile_has_skills` boolean field in the `JobAnalysisResponse`. This field SHALL be `true` when the authenticated user's profile contains at least one skill, and `false` when the profile's skills list is empty. This field enables frontends to distinguish between "no skills matched because the user has no profile skills" and "no skills matched because the job lists no skills or none matched."

#### Scenario: User profile has skills
- **WHEN** a job is analyzed for a user whose profile contains `skills: ["Python", "FastAPI"]`
- **THEN** the analysis response SHALL include `profile_has_skills: true`

#### Scenario: User profile has no skills
- **WHEN** a job is analyzed for a user whose profile contains `skills: []`
- **THEN** the analysis response SHALL include `profile_has_skills: false`

#### Scenario: Profile was just cleared via delete-resume
- **WHEN** a user deletes their resume data (clearing skills to `[]`) and then analyzes a job
- **THEN** the analysis response SHALL include `profile_has_skills: false` with empty `matched_skills` and all job skills appearing in `missing_skills`
