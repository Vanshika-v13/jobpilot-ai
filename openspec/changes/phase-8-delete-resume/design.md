## Context

Phase 7.6 added resume upload (`POST /api/v1/profile/upload-resume`) which populates five resume-derived fields on the user's profile: `resume_text`, `skills`, `experience_years`, `education`, and `preferred_roles`. These fields are stored alongside user-managed fields (`preferred_locations`, `preferred_location`) in the `user_profiles` MongoDB collection.

There is currently no way to undo a resume upload. Users who want to clear their resume data must manually reset each field. This change adds a single `DELETE /api/v1/profile/resume` endpoint that atomically resets all five resume-derived fields to their defaults without touching the profile document itself or user-managed fields.

The existing `profile.py` router (at `/api/v1/profile`) already hosts `POST /upload-resume`. The delete endpoint is added to the same router, keeping all resume-related operations under the `/profile` prefix.

The JD analysis agent (`jd_analysis_agent.py`) computes `matched_skills` and `missing_skills` by comparing the user's `profile.skills` against the job's extracted required/preferred skills. When `profile.skills` is empty, both lists are empty — but the current response provides no signal to distinguish "empty because the user has no skills on their profile" from "empty because the job listed no skills." A new `profile_has_skills` boolean on the analysis response resolves this.

## Goals / Non-Goals

**Goals:**
- Implement `DELETE /api/v1/profile/resume` that resets `resume_text`, `skills`, `experience_years`, `education`, `preferred_roles` to their default values.
- Protect the endpoint with `get_current_user` (same JWT auth pattern as all other protected endpoints).
- Return the updated profile document after the reset.
- Add a `profile_has_skills` field to the `JobAnalysisResponse` so frontends can show a contextual hint when the profile has no skills.
- Write comprehensive tests for the new endpoint.
- Update `docs/api.md` with the new endpoint documentation.

**Non-Goals:**
- Deleting the profile document or user account.
- Modifying user-managed fields (`preferred_locations`, `preferred_location`).
- Implementing the frontend "Delete Resume" button or the empty-profile UX hint (these are Phase 8 frontend scope — documented in the proposal for context only).
- Adding a "partial reset" capability (e.g., clearing only skills but keeping education).
- Adding a resume history or undo stack.

## Decisions

### Reset Strategy: Atomic `$set` with Explicit Defaults

The delete endpoint uses a single `$set` operation with all five fields set to their default values:

```python
clear_fields = {
    "resume_text": None,
    "skills": [],
    "experience_years": 0.0,
    "education": None,
    "preferred_roles": [],
}
```

**Why not `$unset`?** Using `$unset` would remove the fields from the document entirely, which could cause `KeyError` or missing-field issues in code that reads the profile and assumes these fields exist (e.g., `profile.get("skills", [])` would still work, but direct `profile["skills"]` access would fail). Setting to defaults is safer and consistent with the `get_or_create_profile()` default document shape.

**Why not a generic "update profile" call?** The existing `update_profile_by_user_id()` could technically be used with the clear fields as `update_fields`. However, creating a dedicated `clear_resume_fields_by_user_id()` helper makes the intent explicit, prevents accidental misuse (you can't accidentally pass wrong fields), and provides a clean function name for test mocking.

### Endpoint Placement: Same `profile.py` Router

The delete endpoint goes on the existing `profile.py` router (`backend/api/v1/profile.py`) which already handles `POST /upload-resume`. This keeps all resume lifecycle operations together:
- `POST /profile/upload-resume` — add/replace resume data
- `DELETE /profile/resume` — clear resume data

The plural `profiles.py` router handles CRUD operations on the profile document itself.

### Response Model: Reuse `UserProfileResponse`

The delete endpoint returns `UserProfileResponse` directly rather than creating a new response model. The response is simply the updated profile after clearing fields — there is no additional metadata needed. This avoids unnecessary schema proliferation.

### `profile_has_skills` Field on Job Analysis Response

Adding a single boolean `profile_has_skills` to `JobAnalysisResponse` is the minimal-impact approach:
- The field is computed at query time from the profile's skills list (`len(user_skills) > 0`).
- It does not require any schema changes to the MongoDB `jobs` collection or cached analysis data.
- It gives the frontend exactly the signal it needs to show the empty-profile hint vs. a genuine "no matching skills" state.

**Alternative considered**: Returning a `reason` string (e.g., `"no_profile_skills"`, `"no_job_skills"`, `"no_match"`). This was rejected as over-engineered — the boolean is sufficient and keeps the API simple. The frontend only needs to know one thing: does the user have skills on their profile?

### Error Handling

| Scenario | HTTP Status | Response |
|---|---|---|
| No auth token / expired token | 401 | Standard JWT 401 from `get_current_user` |
| Profile not found for user | 404 | `{"detail": "Profile not found"}` |
| Database update fails | 500 | `{"detail": "Failed to clear resume data"}` |

The 404 case is unlikely (profiles are auto-created on first search/resume upload via `get_or_create_profile`) but must be handled for completeness.

## Risks / Trade-offs

- **Risk**: User accidentally clicks "Delete Resume" and loses their profile data.
  - *Mitigation*: The frontend (Phase 8) should show a confirmation dialog before calling the endpoint. The backend operation is intentionally one-way — there is no undo. This is documented behavior.
- **Risk**: Cached job analysis data becomes stale after resume deletion (the cached `skill_match_score` was computed with the old profile skills).
  - *Mitigation*: This is an existing limitation of the caching system, not specific to this change. The analysis cache in the `jobs` collection uses `skill_match_score is not None` as the cache key. A full invalidation strategy is out of scope; users can re-analyze individual jobs to get updated scores. Documenting this as a known behavior.
- **Risk**: The `profile_has_skills` field adds a contract that the frontend depends on. If the field is missing, the frontend might show incorrect UI.
  - *Mitigation*: The field has a default value (`False`) in the Pydantic schema, so it's always present in the response even if the agent code fails to set it.
