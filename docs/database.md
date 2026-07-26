# Database Schema

> Single source of truth for all MongoDB collections. Other docs (`api.md`, `agents.md`) reference this file — they must not redefine fields.

Database: **jobpilot**

---

## 1. `users`

Basic authentication and account info.

| Field | Type | Purpose |
|---|---|---|
| `_id` | ObjectId | Primary key |
| `email` | string | Unique login identifier |
| `password_hash` | string | Hashed password (bcrypt) |
| `full_name` | string | Display name |
| `created_at` | datetime | Account creation timestamp |
| `updated_at` | datetime | Last profile update |

---

## 2. `user_profiles`

Extended profile used by AI agents for matching and ranking.

| Field | Type | Purpose |
|---|---|---|
| `_id` | ObjectId | Primary key |
| `user_id` | ObjectId | Reference to `users._id` |
| `skills` | string[] | Technical and soft skills |
| `experience_years` | number | Total years of experience |
| `education` | string | Highest qualification |
| `preferred_roles` | string[] | Target job titles (e.g. "Backend Developer") |
| `preferred_locations` | string[] | Target cities or "Remote" |
| `resume_text` | string | Plain-text resume content for AI processing |
| `updated_at` | datetime | Last profile update |

---

## 3. `job_searches`

Record of each search a user triggers. Inputs only — results link to `jobs`.

| Field | Type | Purpose |
|---|---|---|
| `_id` | ObjectId | Primary key |
| `user_id` | ObjectId | Reference to `users._id` |
| `query` | string | Free-text search term (e.g. "Python developer") |
| `location` | string | Location filter applied |
| `source` | string | Portal targeted (e.g. "internshala", "unstop", "all") |
| `filters` | object | Any additional filters (experience, salary range, etc.) |
| `status` | string | `pending` · `running` · `completed` · `failed` |
| `job_count` | number | Number of jobs returned |
| `created_at` | datetime | When the search was initiated |

---

## 4. `jobs`

Standardized job object scraped and normalized from any portal. This is the core collection that agents write to and the frontend reads from.

| Field | Type | Purpose |
|---|---|---|
| `_id` | ObjectId | Primary key |
| `search_id` | ObjectId | Reference to `job_searches._id` that found this job |
| `company` | string | Company name |
| `role` | string | Job title |
| `location` | string | Job location or "Remote" |
| `salary` | string | Salary range as displayed on portal (may be "Not disclosed") |
| `apply_link` | string | Direct URL to the job listing |
| `posted_date` | string | Date posted as shown on portal |
| `source` | string | Portal it was scraped from (`internshala`, `unstop`) |
| `required_skills` | string[] | Skills listed as mandatory |
| `preferred_skills` | string[] | Skills listed as nice-to-have |
| `raw_description` | string | Full job description text, unmodified |
| `experience_required` | string | Experience range (e.g. "0-2 years") |
| `job_type` | string | `full-time` · `part-time` · `contract` · `internship` |
| `scraped_at` | datetime | When the job was scraped |
| `skill_match_score` | number | Score (0-100) set by JD Analysis Agent (populated after POST /jobs/{id}/analyze is called, cached) |
| `matched_skills` | string[] | Skills present in both job description and user profile, set by JD Analysis Agent |
| `missing_skills` | string[] | Required/preferred skills missing from user profile, set by JD Analysis Agent |
| `learning_priority` | string[] | Missing skills ordered by importance, set by JD Analysis Agent |
| `jd_summary` | string | Summary of job description, set by JD Analysis Agent |

### Example Document

```json
{
  "_id": "665f1a2b3c4d5e6f7a8b9c0d",
  "search_id": "665f19003c4d5e6f7a8b9c01",
  "company": "Zeta Tech",
  "role": "Backend Development Intern",
  "location": "Bangalore, India",
  "salary": "₹15,000 / month",
  "apply_link": "https://internshala.com/internship/detail/backend-development-internship-in-bangalore-at-zeta-tech-123456",
  "posted_date": "2025-07-20",
  "source": "internshala",
  "required_skills": ["Python", "FastAPI", "MongoDB", "REST APIs"],
  "preferred_skills": ["Docker", "Redis"],
  "raw_description": "We are looking for a Backend Development Intern with strong foundation in Python and FastAPI. The duration of this internship is 6 months...",
  "experience_required": "0-1 years",
  "job_type": "internship",
  "scraped_at": "2025-07-22T10:30:00Z"
}
```

---

## 5. `saved_jobs` — *V2 (future)*

User's bookmarked/saved jobs for later review.

| Field | Type | Purpose |
|---|---|---|
| `_id` | ObjectId | Primary key |
| `user_id` | ObjectId | Reference to `users._id` |
| `job_id` | ObjectId | Reference to `jobs._id` |
| `notes` | string | Optional user notes |
| `saved_at` | datetime | When the job was saved |

---

## 6. `search_history` — *V2 (future)*

Queryable log of a user's past searches for suggestions and analytics.

| Field | Type | Purpose |
|---|---|---|
| `_id` | ObjectId | Primary key |
| `user_id` | ObjectId | Reference to `users._id` |
| `search_id` | ObjectId | Reference to `job_searches._id` |
| `query` | string | Denormalized search term for fast lookup |
| `result_count` | number | Jobs returned |
| `searched_at` | datetime | Timestamp |
