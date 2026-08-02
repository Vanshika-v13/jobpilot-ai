# API Reference

> Field definitions live in [database.md](./database.md) — this file only lists endpoints and their inputs/outputs.

Base URL: `http://localhost:8000/api/v1`

---

### `GET /health`

Health check — confirms the server and database connection are up. **(Public / Unprotected)**

- **Request:** none
- **Response:** `status`, `db_connected`, `timestamp`

---

### `POST /auth/signup`

Creates a new user account. **(Public)**

- **Request:** `email`, `password`, `full_name`
- **Response:** `access_token`, `token_type` (returns a JWT access token immediately upon signup)

---

### `POST /auth/login`

Authenticates a user and returns a JWT access token. **(Public)**

- **Request:** `email`, `password`
- **Response:** `access_token`, `token_type`

---

### `POST /search`

Triggers a job search across configured portals and returns a ranked list of results. **(Protected)**

- **Headers:** `Authorization: Bearer <token>`
- **Request:** `role`, `location`, `experience`, `skills`, `source` (optional, defaults to "all")
- **Response:** `search_id`, `job_count`, `jobs[]` (each entry follows `jobs` collection shape from database.md)
- *Note:* The user profile is looked up/created automatically based on the authenticated user's ID.

---

### `POST /jobs/{id}/analyze`

Runs JD analysis and skill-gap comparison against the user's profile for a single job. **(Protected)**

- **Headers:** `Authorization: Bearer <token>`
- **Request:** none (profile is automatically derived from the authenticated user)
- **Response:** `job_id`, `matched_skills`, `missing_skills`, `skill_match_score`, `summary`

---

### `POST /jobs/{id}/interview-questions`

Generates role-specific interview questions for a single job based on its description. **(Protected)**

- **Headers:** `Authorization: Bearer <token>`
- **Request:** `question_count` (optional, default 10)
- **Response:** `job_id`, `questions[]` (each: `question`, `topic`, `difficulty`)

---

### `POST /export`

Exports one or more jobs to a downloadable file. **(Protected)**

- **Headers:** `Authorization: Bearer <token>`
- **Request:** `job_ids[]`, `format` (`excel` | `pdf`)
- **Response:** `file_url`, `format`, `job_count`

---

### `POST /profiles`

Creates or updates the authenticated user's profile. **(Protected)**

- **Headers:** `Authorization: Bearer <token>`
- **Request:** `skills` (optional), `experience_years` (optional), `education` (optional), `preferred_roles` (optional), `preferred_locations` (optional), `resume_text` (optional)
- **Response:** Updates and returns the `user_profiles` document
- *Note:* The profile is automatically linked to the authenticated user's ID.

---

### `GET /profiles/{id}`

Get a user profile by ID. **(Protected)**

- **Headers:** `Authorization: Bearer <token>`
- **Request:** `id` (path param)
- **Response:** profile document representation

---

### `POST /profile/upload-resume`

Uploads a PDF resume, extracts the text, uses the LLM to structure details, and updates the profile. **(Protected)**

- **Headers:** `Authorization: Bearer <token>`
- **Request:** `file` (PDF upload, multipart/form-data)
- **Response:** Updates and returns the `user_profiles` document (`user_id`, `skills`, `experience_years`, `education`, `resume_text`)

---

### `DELETE /profile/resume`

Clears all resume-derived fields on the authenticated user's profile, resetting them to defaults. **(Protected)**

- **Headers:** `Authorization: Bearer <token>`
- **Request:** none
- **Response:** The updated profile document with reset resume fields (`resume_text` -> `None`, `skills` -> `[]`, `experience_years` -> `0.0`, `education` -> `None`, `preferred_roles` -> `[]`)

---

## V2 Endpoints *(future — not yet designed)*


- `GET /saved-jobs` — list user's bookmarked jobs
- `POST /save-job` — bookmark a job
