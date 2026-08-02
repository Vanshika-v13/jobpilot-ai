## 1. Database Helper

- [x] 1.0 Add `clear_resume_fields_by_user_id(user_id: str)` to `backend/database/user_profiles.py`:
  - Uses `find_one_and_update` with `$set` to reset: `resume_text` → `None`, `skills` → `[]`, `experience_years` → `0.0`, `education` → `None`, `preferred_roles` → `[]`, `updated_at` → `datetime.utcnow()`.
  - Returns the updated document (using `ReturnDocument.AFTER`).
  - Converts `user_id` string to `ObjectId` for the query filter (same pattern as `update_profile_by_user_id`).
  - Returns `None` if no profile found for the given `user_id`.

## 2. API Endpoint

- [x] 2.0 Add `DELETE /resume` route to `backend/api/v1/profile.py`:
  - `@router.delete("/resume", response_model=UserProfileResponse)`
  - Parameter: `user_id: str = Depends(get_current_user)`.
  - Call `clear_resume_fields_by_user_id(user_id)`.
  - If result is `None`, raise `HTTPException(404, "Profile not found")`.
  - Serialize `_id` and `user_id` fields to strings (same pattern as `upload_resume`).
  - Return the updated profile document.
  - Import `UserProfileResponse` from `schemas.profile` and `clear_resume_fields_by_user_id` from `database.user_profiles`.

## 3. Job Analysis Enhancement

- [x] 3.0 Add `profile_has_skills: bool = False` field to `JobAnalysisResponse` in `backend/schemas/jobs.py`.

- [x] 3.1 Update `analyze_jd()` in `backend/agents/jd_analysis_agent.py` to populate `profile_has_skills`:
  - After fetching the profile and extracting `user_skills = profile.get("skills", [])`, set `profile_has_skills = len(user_skills) > 0`.
  - Add `"profile_has_skills": profile_has_skills` to the returned result dict in all code paths (cached result path, LLM failure fallback path, and success path).

## 4. Testing

- [x] 4.0 Create `backend/tests/test_delete_resume.py` with the following test cases:

  **Endpoint tests (mocked DB):**
  - `test_delete_resume_success`: Mock `clear_resume_fields_by_user_id` to return an updated profile with default values. Verify HTTP 200 and that all resume fields are reset.
  - `test_delete_resume_unauthenticated`: Send `DELETE /api/v1/profile/resume` without auth headers. Verify HTTP 401.
  - `test_delete_resume_profile_not_found`: Mock `clear_resume_fields_by_user_id` to return `None`. Verify HTTP 404 with `"Profile not found"` detail.
  - `test_delete_resume_preserves_user_fields`: Mock `clear_resume_fields_by_user_id` to return a profile with `preferred_locations: ["Bangalore"]` intact. Verify the response includes the preserved user-managed fields.
  - `test_delete_resume_idempotent`: Mock `clear_resume_fields_by_user_id` to return a profile already at defaults. Verify HTTP 200.

  **Job analysis `profile_has_skills` tests:**
  - `test_analyze_response_includes_profile_has_skills_true`: Mock a profile with skills and verify `profile_has_skills` is `true` in the analysis response.
  - `test_analyze_response_includes_profile_has_skills_false`: Mock a profile with empty skills and verify `profile_has_skills` is `false`.

- [x] 4.1 Run the full pytest suite to verify no regressions: `pytest backend/tests/ -v`.

## 5. Documentation

- [x] 5.0 Update `docs/api.md` to add the `DELETE /api/v1/profile/resume` endpoint documentation:
  - Method: DELETE
  - Path: `/profile/resume`
  - Auth: Protected (Bearer token)
  - Request: none
  - Response: Updated `user_profiles` document with resume fields reset to defaults
  - Add between the existing `POST /profile/upload-resume` entry and the V2 Endpoints section.

- [x] 5.1 Update `docs/completed_features.md` after implementation is verified.
