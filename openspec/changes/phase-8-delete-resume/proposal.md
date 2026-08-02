## Why

Users can upload a resume via `POST /api/v1/profile/upload-resume`, which populates their profile with extracted skills, experience, education, and preferred roles. However, there is currently no way to **undo** this operation — a user who wants to start fresh, correct a bad extraction, or remove their resume data must manually clear each field. A dedicated `DELETE /api/v1/profile/resume` endpoint provides a clean, single-action reset of all resume-derived profile data without deleting the profile document or user account.

Additionally, when a user's profile has **no skills at all** (because they have never uploaded a resume or have deleted it), the Job Details page currently shows empty `matched_skills` / `missing_skills` sections with no explanation. This is confusing — the user doesn't know whether the job has no listed skills or whether they simply haven't set up their profile. A contextual UI hint resolves this ambiguity.

## What Changes

- **New Endpoint**: `DELETE /api/v1/profile/resume`
  - Protected by `get_current_user` (JWT auth).
  - Clears all resume-derived fields on the authenticated user's profile: `resume_text` → `None`, `skills` → `[]`, `experience_years` → `0.0`, `education` → `None`, `preferred_roles` → `[]`.
  - Does **NOT** delete the profile document or user account.
  - Does **NOT** modify user-managed fields (`preferred_locations`, `preferred_location`).
  - Returns the updated profile document.

- **New Database Helper**: `clear_resume_fields_by_user_id(user_id)` in `database/user_profiles.py`
  - Resets the five resume-derived fields to their default values using `$set`.
  - Returns the updated profile document.

- **New Response Schema**: `ResumeDeleteResponse` in `schemas/profile.py`
  - Response model for the delete endpoint (same shape as `UserProfileResponse`).

- **Job Analysis Response Enhancement**: Add a `profile_has_skills` boolean field to `JobAnalysisResponse` in `schemas/jobs.py`
  - Set to `true` when the user's profile has at least one skill, `false` otherwise.
  - Enables the frontend to distinguish between "no skills matched because the job lists none" vs "no skills matched because the user has no profile skills."

- **Frontend UX Hint** (Phase 8 scope): When `profile_has_skills` is `false`, the Job Details page displays:
  > "Add skills to your profile or upload a resume for personalized matching."
  instead of showing empty matched/missing skills sections.

- **Frontend "Delete Resume" Button** (Phase 8 scope): The Profile page includes a "Delete Resume" button that calls `DELETE /api/v1/profile/resume` and refreshes the profile state.

## Capabilities

### New Capabilities
- `delete-resume`: Ability for authenticated users to clear all resume-derived profile data in a single API call, resetting skills, experience, education, preferred roles, and resume text to defaults.

### Modified Capabilities
- `jd-analysis`: Add `profile_has_skills` field to the analysis response so frontends can differentiate between "no skills matched" due to an empty profile vs. the job listing no skills.

## Impact

- `backend/api/v1/profile.py`: Add `DELETE /resume` route handler.
- `backend/database/user_profiles.py`: Add `clear_resume_fields_by_user_id()` helper.
- `backend/schemas/profile.py`: Add `ResumeDeleteResponse` model.
- `backend/schemas/jobs.py`: Add `profile_has_skills` field to `JobAnalysisResponse`.
- `backend/agents/jd_analysis_agent.py`: Populate `profile_has_skills` based on the user's profile skills list.
- `backend/tests/test_delete_resume.py`: **[NEW]** Test suite for the delete endpoint.
- `docs/api.md`: Document the new `DELETE /api/v1/profile/resume` endpoint.
- Does **NOT** touch: `frontend/` (frontend changes are Phase 8 scope, documented here for context), `backend/tools/`, `backend/agents/` (except the `profile_has_skills` addition to `jd_analysis_agent.py`).
