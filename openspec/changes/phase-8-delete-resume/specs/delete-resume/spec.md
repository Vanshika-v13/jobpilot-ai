## ADDED Requirements

### Requirement: Authenticated user can clear all resume-derived profile data
The system SHALL provide a `DELETE /api/v1/profile/resume` endpoint that resets all resume-derived fields on the authenticated user's profile to their default/empty values. The endpoint SHALL be protected by the `get_current_user` dependency. The profile document and user account SHALL NOT be deleted. User-managed fields (`preferred_locations`, `preferred_location`) SHALL NOT be modified.

#### Scenario: Successful resume data deletion
- **WHEN** an authenticated user sends `DELETE /api/v1/profile/resume` with a valid JWT token
- **THEN** the system resets `resume_text` to `None`, `skills` to `[]`, `experience_years` to `0.0`, `education` to `None`, `preferred_roles` to `[]` on the user's profile and returns the updated profile document with HTTP 200

#### Scenario: Profile does not exist
- **WHEN** an authenticated user sends `DELETE /api/v1/profile/resume` but no profile document exists for their `user_id`
- **THEN** the system returns HTTP 404 with `{"detail": "Profile not found"}`

#### Scenario: Unauthenticated request
- **WHEN** a request is sent to `DELETE /api/v1/profile/resume` without a valid JWT token
- **THEN** the system returns HTTP 401 with the standard authentication error

#### Scenario: User-managed fields are preserved
- **WHEN** an authenticated user has `preferred_locations: ["Bangalore"]` and `preferred_location: "Bangalore"` on their profile and sends `DELETE /api/v1/profile/resume`
- **THEN** `preferred_locations` and `preferred_location` remain unchanged in the returned profile document

#### Scenario: Idempotent deletion
- **WHEN** an authenticated user sends `DELETE /api/v1/profile/resume` on a profile that already has empty/default resume fields
- **THEN** the system returns HTTP 200 with the profile document (fields remain at defaults)
