# API Reference

> Field definitions live in [database.md](./database.md) — this file only lists endpoints and their inputs/outputs.

Base URL: `http://localhost:8000/api/v1`

---

### `GET /health`

Health check — confirms the server and database connection are up.

- **Request:** none
- **Response:** `status`, `db_connected`, `timestamp`

---

### `POST /search`

Triggers a job search across configured portals and returns a ranked list of results.

- **Request:** `role`, `location`, `experience`, `skills`, `source` (optional, defaults to "all")
- **Response:** `search_id`, `job_count`, `jobs[]` (each entry follows `jobs` collection shape from database.md)

---

### `POST /jobs/{id}/analyze`

Runs JD analysis and skill-gap comparison against the user's profile for a single job.

- **Request:** `job_id` (path param), `user_id`
- **Response:** `job_id`, `matched_skills`, `missing_skills`, `skill_match_score`, `summary`

---

### `POST /jobs/{id}/interview-questions`

Generates role-specific interview questions for a single job based on its description.

- **Request:** `job_id` (path param), `user_id`, `question_count` (optional, default 10)
- **Response:** `job_id`, `questions[]` (each: `question`, `topic`, `difficulty`)

---

### `POST /export`

Exports one or more jobs to a downloadable file.

- **Request:** `job_ids[]`, `format` (`excel` | `pdf`)
- **Response:** `file_url`, `format`, `job_count`

---

### `POST /auth/signup`

Creates a new user account.

- **Request:** `email`, `password`, `full_name` (as defined in `users` schema)
- **Response:** `user_id` (matching `users._id`), `email`, `full_name`

---

### `POST /auth/login`

Authenticates a user and returns a JWT access token.

- **Request:** `email`, `password`
- **Response:** `access_token`, `token_type`

---

### `POST /profile/upload-resume`

Uploads a PDF resume, extracts the text, uses the LLM to structure details, and updates the profile.

- **Request:** `file` (PDF upload, multipart/form-data), headers: `Authorization: Bearer <token>`
- **Response:** Updates and returns the `user_profiles` document (`user_id`, `skills`, `experience_years`, `education`, `resume_text`)

---

## V2 Endpoints *(future — not yet designed)*

- `GET /saved-jobs` — list user's bookmarked jobs
- `POST /save-job` — bookmark a job
