## Context

Phase 7.5 introduces Authentication to the JobPilot AI backend. Moving forward, the server will enforce token-based security on all data-retrieval and agent-execution operations. Rather than clients supplying arbitrary profile identifiers, the authenticated identity (retrieved via JWT decoding) will act as the single source of truth for loading user profiles, running searches, and calculating matching scores.

## Goals / Non-Goals

**Goals:**
- Implement `POST /api/v1/auth/signup` and `POST /api/v1/auth/login` as specified in `api.md`.
- Establish secure password storage using bcrypt.
- Implement token-based authorization using PyJWT with a 7-day (168 hours) expiry.
- Design a reusable `get_current_user` dependency to validate headers and extract `user_id`.
- Protect all data and agent endpoints (`/search`, `/jobs/{id}/analyze`, `/jobs/{id}/interview-questions`, `/export`, `/profiles`, `/profiles/{id}`) with this dependency.
- Resolve user profiles automatically from the JWT payload, generating a default profile if one does not exist.

**Non-Goals:**
- Building frontend authentication flows (postponed to Phase 8).
- Handling OAuth2 social sign-ins (Google, GitHub, etc.) — standard email/password only.
- Implement JWT refresh token rotations (unnecessary for Phase 1 V1 requirements).

## Decisions

- **Cryptographic Library Choice**:
  - We choose `PyJWT` for JWT signing and decoding due to its simplicity, strict adherence to standards, and lack of system-level dependencies.
  - We choose the `bcrypt` library directly for password hashing, ensuring strong, standard resistance to brute-force attacks and avoiding wrapper package dependencies like passlib.
- **JWT Configuration**:
  - Payload claims:
    ```json
    {
      "sub": "user_id_string",
      "exp": 1722585600
    }
    ```
  - Expiry duration: 7 days (168 hours). This is a deliberate UX design decision to support a standard "stay logged in" session experience for a consumer-facing app.
  - Configuration settings: Load `JWT_SECRET_KEY` and optional `JWT_ALGORITHM` (defaulting to HS256) from environmental variables (`.env`).
- **Database Schema**:
  - The `users` collection stores:
    ```json
    {
      "_id": "ObjectId",
      "email": "user@example.com",
      "password_hash": "$2b$12$...",
      "full_name": "Full Name",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
    ```
- **Profile Resolution & Fallback**:
  - When a protected route calls `get_current_user`, the user's ID is retrieved.
  - The endpoint then queries the `user_profiles` collection using `{"user_id": ObjectId(user_id)}`.
  - If no profile is found, the backend creates a profile document automatically with default values (empty skills, 0.0 experience, etc.) and associates it with the user ID before continuing execution. This prevents failure cases when new users run search or analysis immediately.
- **Breaking API Changes**:
  - `POST /api/v1/search`: Accepts `{ "role": "...", "location": "...", "experience": "...", "skills": ["..."], "source": "..." }`. The `profile_id` is removed from the request schema.
  - `POST /api/v1/jobs/{id}/analyze`: Accepts an empty request body `{}` (instead of `{ "profile_id": "..." }` or `{ "user_id": "..." }`).
  - `POST /api/v1/jobs/{id}/interview-questions`: Accepts `{ "question_count": 10 }` (unchanged schema, but now requires the token header).
  - `POST /api/v1/profiles`: Creates/updates the authenticated user's profile. Does not accept client-provided `user_id`.

## Risks / Trade-offs

- **Risk**: Database query overhead for validating user profile existence on every request.
  - *Mitigation*: Ensure there is a unique index on `user_profiles.user_id` and `users.email`.
- **Risk**: Existing test profile data (created before auth existed) will become orphaned once auth is enforced.
  - *Mitigation*: This is expected and acceptable for V1. New accounts will automatically create their own isolated profiles. Old sandbox profiles can be purged or manually reassigned if needed.
- **Risk**: Breaking existing integration tests.
  - *Mitigation*: Provide test-suite helpers in `backend/tests/` to create a mock user, generate a token, and inject `Authorization: Bearer <token>` headers automatically for all endpoint assertions.
