import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from bson import ObjectId

from main import app
from core.config import settings
from core.auth import create_access_token, verify_access_token
from core.security import hash_password, verify_password


# --- Unit tests for core/security.py ---

def test_hash_password_returns_string():
    hashed = hash_password("mypassword123")
    assert isinstance(hashed, str)
    assert hashed != "mypassword123"

def test_verify_password_correct():
    hashed = hash_password("mypassword123")
    assert verify_password("mypassword123", hashed) is True

def test_verify_password_incorrect():
    hashed = hash_password("mypassword123")
    assert verify_password("wrongpassword", hashed) is False

def test_verify_password_invalid_hash():
    assert verify_password("mypassword123", "not-a-valid-hash") is False


# --- Unit tests for core/auth.py ---

def test_create_access_token_returns_string():
    token = create_access_token("507f1f77bcf86cd799439011")
    assert isinstance(token, str)

def test_create_access_token_contains_sub_claim():
    user_id = "507f1f77bcf86cd799439011"
    token = create_access_token(user_id)
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == user_id

def test_create_access_token_has_expiry():
    token = create_access_token("507f1f77bcf86cd799439011")
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert "exp" in payload

def test_verify_access_token_valid():
    user_id = "507f1f77bcf86cd799439011"
    token = create_access_token(user_id)
    result = verify_access_token(token)
    assert result == user_id

def test_verify_access_token_expired():
    payload = {
        "sub": "507f1f77bcf86cd799439011",
        "exp": datetime.utcnow() - timedelta(seconds=1),
        "iat": datetime.utcnow() - timedelta(days=8)
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    result = verify_access_token(token)
    assert result is None

def test_verify_access_token_invalid_signature():
    payload = {
        "sub": "507f1f77bcf86cd799439011",
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
    result = verify_access_token(token)
    assert result is None

def test_verify_access_token_malformed():
    result = verify_access_token("not.a.valid.token")
    assert result is None

def test_verify_access_token_missing_sub():
    payload = {
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    result = verify_access_token(token)
    assert result is None


# --- Integration tests for /auth/signup and /auth/login endpoints ---

@pytest.mark.asyncio
@patch("api.v1.auth.get_user_by_email")
@patch("api.v1.auth.create_user")
async def test_signup_success(mock_create_user, mock_get_user_by_email):
    user_id = str(ObjectId())
    mock_get_user_by_email.return_value = None  # No existing user
    mock_create_user.return_value = user_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com", "password": "securepass123", "full_name": "Test User"}
        )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    mock_create_user.assert_called_once()

@pytest.mark.asyncio
@patch("api.v1.auth.get_user_by_email")
async def test_signup_duplicate_email(mock_get_user_by_email):
    mock_get_user_by_email.return_value = {"_id": ObjectId(), "email": "test@example.com"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com", "password": "securepass123", "full_name": "Test User"}
        )

    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

@pytest.mark.asyncio
@patch("api.v1.auth.get_user_by_email")
async def test_login_success(mock_get_user_by_email):
    user_id = ObjectId()
    mock_get_user_by_email.return_value = {
        "_id": user_id,
        "email": "test@example.com",
        "password_hash": hash_password("securepass123"),
        "full_name": "Test User"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "securepass123"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
@patch("api.v1.auth.get_user_by_email")
async def test_login_wrong_password(mock_get_user_by_email):
    mock_get_user_by_email.return_value = {
        "_id": ObjectId(),
        "email": "test@example.com",
        "password_hash": hash_password("correctpassword"),
        "full_name": "Test User"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"}
        )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

@pytest.mark.asyncio
@patch("api.v1.auth.get_user_by_email")
async def test_login_nonexistent_user(mock_get_user_by_email):
    mock_get_user_by_email.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "somepassword"}
        )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


# --- Auth header format checks ---

@pytest.mark.asyncio
async def test_protected_endpoint_no_auth_header():
    """Endpoints requiring auth should return 401 when no Authorization header is sent."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/profiles/507f1f77bcf86cd799439011")

    assert response.status_code == 401  # HTTPBearer returns 401 when header is missing

@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token():
    """Endpoints requiring auth should return 401 for invalid tokens."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/profiles/507f1f77bcf86cd799439011",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_endpoint_expired_token():
    """Endpoints requiring auth should return 401 for expired tokens."""
    payload = {
        "sub": "507f1f77bcf86cd799439011",
        "exp": datetime.utcnow() - timedelta(seconds=1),
        "iat": datetime.utcnow() - timedelta(days=8)
    }
    expired_token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/profiles/507f1f77bcf86cd799439011",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

    assert response.status_code == 401
