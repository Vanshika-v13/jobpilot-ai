## 1. Setup and Environment Configuration

- [x] 1.0 Add `PyJWT` and `bcrypt` directly to `backend/requirements.txt`.
- [x] 1.1 Add `JWT_SECRET_KEY` and optional `JWT_ALGORITHM` (defaulting to "HS256") to `backend/.env.example` and the active `backend/.env`.
- [x] 1.2 Update `backend/core/config.py` to parse `jwt_secret_key` and `jwt_algorithm` into the `Settings` class.

## 2. Database and Security Utilities

- [x] 2.0 Create `backend/database/users.py` containing:
  - `create_user(email, password, full_name)`: Hashes password using `bcrypt`, inserts user, returns `user_id`.
  - `get_user_by_email(email)`: Retreives a user by unique email.
  - `get_user_by_id(user_id)`: Retrieves user details.
- [x] 2.1 Update `backend/database/user_profiles.py` to add:
  - `get_profile_by_user_id(user_id)`: Fetches a profile matching a specific `user_id`.
  - `get_or_create_profile(user_id)`: Retrieves a profile by `user_id`, or inserts a new empty/default profile if none exists.
- [x] 2.2 Implement password hashing and verification helpers in a secure utilities file (e.g. `backend/core/security.py`) using `bcrypt`.

## 3. Authentication Dependency

- [x] 3.0 Create `backend/core/auth.py` and implement JWT generation (`create_access_token` with 7-day expiry) and verification logic using `PyJWT`.
- [x] 3.1 Implement `get_current_user` as a FastAPI dependency using `fastapi.security.HTTPBearer`. It should decode the token, validate claims, check expiration, and return the `user_id` string, raising HTTP 401 on failure.

## 4. Schemas and Routing

- [x] 4.0 Create `backend/schemas/auth.py` defining registration and login request/response contracts.
- [x] 4.1 Create router file `backend/api/v1/auth.py` with `/signup` and `/login` endpoints.
- [x] 4.2 Include the authentication router under `/auth` prefix in `backend/api/v1/router.py`.

## 5. Protecting Existing Endpoints and Refactoring Schemas

- [x] 5.0 Update `backend/schemas/search.py` to remove `profile_id` from `SearchRequest`.
- [x] 5.1 Update `backend/schemas/jobs.py` to remove `profile_id` from `JobAnalysisRequest`.
- [x] 5.2 Update `backend/schemas/profile.py` to remove `user_id` from client-facing input schemas, or mark it optional.
- [x] 5.3 Modify `backend/api/v1/profiles.py`:
  - Protect `POST /profiles` and `GET /profiles/{id}` using the auth dependency.
  - Automatically associate new profiles with the authenticated user's ID.
- [x] 5.4 Modify `backend/api/v1/search.py`:
  - Protect the route with `get_current_user`.
  - Resolve the user profile via `get_or_create_profile(user_id)` instead of accepting `profile_id` from request.
- [x] 5.5 Modify `backend/api/v1/jobs.py`:
  - Protect both `/jobs/{id}/analyze` and `/jobs/{id}/interview-questions` with `get_current_user`.
  - Resolve the user profile automatically via `get_or_create_profile` instead of accepting it in the payload.
- [x] 5.6 Modify `backend/api/v1/export.py`:
  - Protect the route with `get_current_user`.

## 6. Testing and Verification

- [x] 6.0 Create `backend/tests/test_auth.py` verifying registration, login with correct/incorrect credentials, token expiration, and auth header format checks.
- [x] 6.1 Update existing endpoint tests (search, analyze, interview questions, export, profiles) to generate a mock token and pass it via authorization headers to ensure compatibility.
- [x] 6.2 Run the entire pytest suite to verify no regressions occur.
