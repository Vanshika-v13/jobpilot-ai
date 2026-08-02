## Why

This change implements Phase 7.5 of the development cycle: Authentication. 
To transition JobPilot AI to a secure, multi-user system, we need robust authentication, user-specific data isolation, and API security. 
Currently, the system allows arbitrary client-supplied `profile_id` parameters, which is insecure and lacks access control. Implementing JWT authentication secures existing endpoints and ensures that user profiles, searches, and analysis results are strictly isolated and linked to the authenticated user.

## What Changes

- **New Authentication Endpoints**:
  - `POST /api/v1/auth/signup`: Accepts `email`, `password`, and `full_name`. Hashes password with the `bcrypt` library, creates a user document in MongoDB, and returns a JWT access token.
  - `POST /api/v1/auth/login`: Accepts `email` and `password`. Verifies against the database hash and returns a JWT access token.
- **JWT Implementation**:
  - Use `PyJWT` for decoding and encoding tokens due to its lightweight profile and standard compliance.
  - Signed using `JWT_SECRET_KEY` from `.env`.
  - Expiry set to 7 days (168 hours) as a deliberate UX decision to provide a standard "stay logged in" experience for a consumer-style app.
- **FastAPI Authentication Dependency**:
  - Create `get_current_user` in `backend/core/auth.py`. This reads the `Authorization: Bearer <token>` header, decodes and validates the token, and returns the authenticated `user_id`.
  - Raises HTTP 401 Unauthorized for missing, invalid, or expired tokens.
- **Endpoint Protection**:
  - Protect the following existing endpoints using `get_current_user`:
    - `POST /api/v1/search`
    - `POST /api/v1/jobs/{id}/analyze`
    - `POST /api/v1/jobs/{id}/interview-questions`
    - `POST /api/v1/export`
    - `POST /api/v1/profiles`
    - `GET /api/v1/profiles/{id}`
  - Keep `GET /api/v1/health` public.
- **Breaking Changes to Request Schemas (Profile Derivation)**:
  - Eliminate client-supplied `profile_id` and `user_id` in request payloads for `POST /search`, `POST /jobs/{id}/analyze`, and `POST /jobs/{id}/interview-questions`.
  - Instead, the backend automatically queries the `user_profiles` collection using the authenticated `user_id` extracted from the JWT.
  - If a user doesn't have a profile yet when accessing these endpoints, a default profile is automatically created in the database.

## Capabilities

### New Capabilities
- `user-authentication`: Ability for users to register, log in, and acquire cryptographically signed JWT access tokens.
- `access-control`: Reusable auth middleware to validate tokens and protect API endpoints from unauthorized actions.
- `profile-auto-resolution`: Seamless retrieval or creation of a user's profile based strictly on their authenticated session context.

## Impact

- `backend/core/config.py`: Add `jwt_secret_key` and other auth settings.
- `backend/core/auth.py`: Reusable token utilities and `get_current_user` FastAPI dependency.
- `backend/database/users.py`: User registration, lookup, and password hashing helper functions.
- `backend/schemas/auth.py`: Request and response models for signup, login, and token response.
- `backend/schemas/search.py`: Remove `profile_id` from `SearchRequest`.
- `backend/schemas/jobs.py`: Remove `profile_id` from `JobAnalysisRequest`.
- `backend/schemas/profile.py`: Remove `user_id` from client-facing input schemas, making it optional/internal.
- `backend/api/v1/auth.py`: Implement signup and login routes.
- `backend/api/v1/router.py`: Include `auth` router.
- `backend/api/v1/search.py`, `backend/api/v1/jobs.py`, `backend/api/v1/export.py`, `backend/api/v1/profiles.py`: Integrate JWT protection and resolve profiles using authenticated user IDs.
- `backend/tests/`: Update existing endpoint tests to include valid auth headers and add new test suite for auth mechanics.
